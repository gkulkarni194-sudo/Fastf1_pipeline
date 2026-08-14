from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from f1_pipeline.physics.aero.downforce_model import estimate_cla_from_lateral_capacity
from f1_pipeline.physics.aero.drag_model import drag_force, estimate_cda_from_coast
from f1_pipeline.physics.constants import constant_from_config
from f1_pipeline.physics.diagnostics import evaluate_status, regression_diagnostics
from f1_pipeline.physics.schemas import IdentifiabilityReport, PhysicsModelResult, PhysicsParameterEstimate
from f1_pipeline.physics.uncertainty import confidence_interval, covariance_from_design, standard_errors


DRAG_MODEL_NAME = "aero_drag_coastdown"
DRAG_MODEL_VERSION = "1.0"
DOWNFORCE_MODEL_NAME = "effective_downforce_lateral_capacity"
DOWNFORCE_MODEL_VERSION = "1.0"


def estimate_drag(telemetry: pd.DataFrame, config: dict[str, Any]) -> PhysicsModelResult:
    model_cfg = config.get("models", {}).get("drag", {})
    ident = IdentifiabilityReport(
        identifiable_parameters=["effective_drag_parameter"],
        non_identifiable_parameters=["drag_coefficient", "frontal_area", "rolling_resistance_without_extra_information"],
        assumptions=[
            "Coastdown-like low throttle, non-braking samples approximate drag-dominated deceleration.",
            "Vehicle mass and air density are configured or assumed, not observed unless supplied upstream.",
        ],
        limitations=["Rolling resistance is not independently separated in the drag-only fit."],
    )
    required = {"speed_ms", "acceleration_longitudinal"}
    if not required.issubset(telemetry.columns):
        return _insufficient(DRAG_MODEL_NAME, DRAG_MODEL_VERSION, ident, len(telemetry), f"missing required columns {sorted(required - set(telemetry.columns))}")

    filtered, reasons = _drag_filter(telemetry, config)
    if len(filtered) < int(model_cfg.get("min_samples", 0)):
        return _insufficient(DRAG_MODEL_NAME, DRAG_MODEL_VERSION, ident, len(telemetry), "too few coastdown samples", reasons, len(filtered))

    rho = constant_from_config(config, "air_density").value
    mass = constant_from_config(config, "vehicle_mass_reference").value
    try:
        cda, design = estimate_cda_from_coast(filtered["speed_ms"].to_numpy(), filtered["acceleration_longitudinal"].to_numpy(), air_density=rho, mass_kg=mass)
        predicted_force = drag_force(filtered["speed_ms"].to_numpy(), air_density=rho, effective_drag_parameter=cda)
        observed_force = -mass * filtered["acceleration_longitudinal"].to_numpy()
        residuals = observed_force - predicted_force
        diagnostics = regression_diagnostics(observed_force, predicted_force, rows_input=len(telemetry), exclusion_reasons=reasons)
        se = (standard_errors(covariance_from_design(design, residuals, 1)) or [None])[0]
        lo, hi = confidence_interval(cda, se, float(config.get("fitting", {}).get("confidence_level", 0.95)))
        status = evaluate_status(diagnostics, model_cfg, {"cda": cda})
        param = PhysicsParameterEstimate(
            parameter_name="effective_drag_parameter",
            value=cda,
            unit="m^2",
            standard_error=se,
            confidence_interval_low=lo,
            confidence_interval_high=hi,
            sample_count=len(filtered),
            model_name=DRAG_MODEL_NAME,
            model_version=DRAG_MODEL_VERSION,
            status=status,
        )
        return PhysicsModelResult(
            model_name=DRAG_MODEL_NAME,
            model_version=DRAG_MODEL_VERSION,
            parameters=[param],
            diagnostics=diagnostics,
            identifiability=ident,
            status=status,
            predictions=_records(filtered, predicted_force, "drag_force_predicted"),
            residuals=_records(filtered, residuals, "drag_force_residual"),
        )
    except Exception as exc:
        return _failed(DRAG_MODEL_NAME, DRAG_MODEL_VERSION, ident, len(telemetry), str(exc), reasons)


def estimate_downforce(telemetry: pd.DataFrame, config: dict[str, Any]) -> PhysicsModelResult:
    model_cfg = config.get("models", {}).get("downforce", {})
    ident = IdentifiabilityReport(
        identifiable_parameters=["effective_downforce_parameter"],
        non_identifiable_parameters=["lift_coefficient", "frontal_area", "tyre_friction_coefficient"],
        assumptions=["High lateral-acceleration samples approximate grip-limited cornering capacity."],
        limitations=["Without direct normal load or tyre friction data, ClA is an effective envelope proxy only."],
    )
    required = {"speed_ms", "acceleration_lateral"}
    if not required.issubset(telemetry.columns):
        return _insufficient(DOWNFORCE_MODEL_NAME, DOWNFORCE_MODEL_VERSION, ident, len(telemetry), f"missing required columns {sorted(required - set(telemetry.columns))}")
    filtered, reasons = _finite_filter(telemetry, ["speed_ms", "acceleration_lateral"], config)
    filtered = filtered[np.abs(filtered["acceleration_lateral"]) > constant_from_config(config, "gravity").value].copy()
    reasons["not_above_1g_lateral_capacity"] = len(telemetry) - sum(reasons.values()) - len(filtered)
    if len(filtered) < int(model_cfg.get("min_samples", 0)):
        return _insufficient(DOWNFORCE_MODEL_NAME, DOWNFORCE_MODEL_VERSION, ident, len(telemetry), "insufficient high-lateral samples", reasons, len(filtered))
    rho = constant_from_config(config, "air_density").value
    mass = constant_from_config(config, "vehicle_mass_reference").value
    g = constant_from_config(config, "gravity").value
    try:
        cla, design = estimate_cla_from_lateral_capacity(filtered["speed_ms"].to_numpy(), filtered["acceleration_lateral"].to_numpy(), air_density=rho, mass_kg=mass, gravity=g)
        predicted = 0.5 * rho * cla * filtered["speed_ms"].to_numpy() ** 2
        observed = mass * (np.abs(filtered["acceleration_lateral"].to_numpy()) - g)
        residuals = observed - predicted
        diagnostics = regression_diagnostics(observed, predicted, rows_input=len(telemetry), exclusion_reasons=reasons)
        se = (standard_errors(covariance_from_design(design, residuals, 1)) or [None])[0]
        lo, hi = confidence_interval(cla, se, float(config.get("fitting", {}).get("confidence_level", 0.95)))
        status = evaluate_status(diagnostics, model_cfg, {"cla": cla})
        return PhysicsModelResult(
            model_name=DOWNFORCE_MODEL_NAME,
            model_version=DOWNFORCE_MODEL_VERSION,
            parameters=[PhysicsParameterEstimate(parameter_name="effective_downforce_parameter", value=cla, unit="m^2", standard_error=se, confidence_interval_low=lo, confidence_interval_high=hi, sample_count=len(filtered), model_name=DOWNFORCE_MODEL_NAME, model_version=DOWNFORCE_MODEL_VERSION, status=status)],
            diagnostics=diagnostics,
            identifiability=ident,
            status=status,
            predictions=_records(filtered, predicted, "downforce_predicted"),
            residuals=_records(filtered, residuals, "downforce_residual"),
        )
    except Exception as exc:
        return _failed(DOWNFORCE_MODEL_NAME, DOWNFORCE_MODEL_VERSION, ident, len(telemetry), str(exc), reasons)


def _drag_filter(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, int]]:
    filtered, reasons = _finite_filter(df, ["speed_ms", "acceleration_longitudinal"], config)
    start = len(filtered)
    min_speed = float(config.get("filtering", {}).get("min_speed_ms", 20.0))
    filtered = filtered[filtered["speed_ms"] >= min_speed]
    reasons["below_min_speed"] = start - len(filtered)
    if "throttle_percent" in filtered.columns:
        start = len(filtered)
        filtered = filtered[filtered["throttle_percent"] <= float(config.get("filtering", {}).get("coast_throttle_max", 5.0))]
        reasons["not_coasting"] = start - len(filtered)
    if bool(config.get("filtering", {}).get("exclude_braking", True)) and "brake_active" in filtered.columns:
        start = len(filtered)
        filtered = filtered[~filtered["brake_active"].astype(bool)]
        reasons["braking"] = start - len(filtered)
    start = len(filtered)
    filtered = filtered[filtered["acceleration_longitudinal"] < 0]
    reasons["not_decelerating"] = start - len(filtered)
    return filtered.copy(), {k: int(v) for k, v in reasons.items() if v}


def _finite_filter(df: pd.DataFrame, columns: list[str], config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, int]]:
    mask = np.ones(len(df), dtype=bool)
    reasons: dict[str, int] = {}
    for col in columns:
        ok = np.isfinite(pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float))
        reasons[f"non_finite_{col}"] = int((mask & ~ok).sum())
        mask &= ok
    if "dt" in df.columns:
        ok = pd.to_numeric(df["dt"], errors="coerce").le(float(config.get("filtering", {}).get("max_gap_seconds", 0.5))).fillna(False).to_numpy()
        reasons["telemetry_gap"] = int((mask & ~ok).sum())
        mask &= ok
    return df.loc[mask].copy(), {k: v for k, v in reasons.items() if v}


def _records(df: pd.DataFrame, values: np.ndarray, value_name: str) -> list[dict[str, Any]]:
    cols = [c for c in ("time", "lap_number", "distance", "speed_ms") if c in df.columns]
    out = df[cols].copy() if cols else pd.DataFrame(index=df.index)
    out["model"] = value_name
    out["value"] = values
    return out.replace({np.nan: None}).to_dict(orient="records")


def _insufficient(name: str, version: str, ident: IdentifiabilityReport, rows: int, warning: str, reasons: dict[str, int] | None = None, used: int = 0) -> PhysicsModelResult:
    result = PhysicsModelResult(model_name=name, model_version=version, identifiability=ident, status="insufficient_data")
    result.diagnostics.rows_input = rows
    result.diagnostics.rows_used = used
    result.diagnostics.rows_excluded = max(rows - used, 0)
    result.diagnostics.exclusion_reasons = reasons or {}
    result.diagnostics.warnings = [warning]
    return result


def _failed(name: str, version: str, ident: IdentifiabilityReport, rows: int, warning: str, reasons: dict[str, int] | None = None) -> PhysicsModelResult:
    result = _insufficient(name, version, ident, rows, warning, reasons)
    result.status = "failed"
    result.diagnostics.convergence_status = "failed"
    return result
