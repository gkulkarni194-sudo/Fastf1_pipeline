from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from f1_pipeline.physics.aero.drag_model import drag_force
from f1_pipeline.physics.constants import constant_from_config
from f1_pipeline.physics.diagnostics import evaluate_status, regression_diagnostics
from f1_pipeline.physics.longitudinal.force_model import effective_wheel_power, longitudinal_force_balance
from f1_pipeline.physics.longitudinal.resistance_model import rolling_resistance_force
from f1_pipeline.physics.schemas import IdentifiabilityReport, PhysicsModelResult, PhysicsParameterEstimate
from f1_pipeline.physics.uncertainty import confidence_interval, covariance_from_design, standard_errors


LONGITUDINAL_MODEL_NAME = "effective_longitudinal_force_proxy"
LONGITUDINAL_MODEL_VERSION = "1.0"


def estimate_longitudinal(telemetry: pd.DataFrame, config: dict[str, Any], drag_cda: float | None = None) -> PhysicsModelResult:
    model_cfg = config.get("models", {}).get("longitudinal", {})
    ident = IdentifiabilityReport(
        identifiable_parameters=["effective_drive_force", "effective_wheel_power"],
        non_identifiable_parameters=["engine_power", "drivetrain_efficiency", "engine_torque_curve"],
        assumptions=["High-throttle non-braking samples approximate drive-limited acceleration.", "Vehicle mass and air density are configured or assumed."],
        limitations=["Drive force is an effective proxy at the wheels, not true engine output."],
    )
    required = {"speed_ms", "acceleration_longitudinal"}
    if not required.issubset(telemetry.columns):
        return _insufficient(len(telemetry), f"missing required columns {sorted(required - set(telemetry.columns))}", ident)
    filtered, reasons = _filter(telemetry, config)
    if len(filtered) < int(model_cfg.get("min_samples", 0)):
        return _insufficient(len(telemetry), "too few high-throttle samples", ident, reasons, len(filtered))
    mass = constant_from_config(config, "vehicle_mass_reference").value
    rho = constant_from_config(config, "air_density").value
    gravity = constant_from_config(config, "gravity").value
    crr = constant_from_config(config, "rolling_resistance_reference").value
    drag = drag_force(filtered["speed_ms"].to_numpy(), air_density=rho, effective_drag_parameter=drag_cda or 0.0)
    rolling = rolling_resistance_force(rolling_resistance_coefficient=crr, mass_kg=mass, gravity=gravity)
    force = longitudinal_force_balance(filtered["acceleration_longitudinal"].to_numpy(), mass_kg=mass, drag_force_n=drag, rolling_force_n=rolling)
    prediction = np.full(len(filtered), float(np.mean(force)))
    residuals = force - prediction
    design = np.ones((len(filtered), 1))
    diagnostics = regression_diagnostics(force, prediction, rows_input=len(telemetry), exclusion_reasons=reasons)
    se = (standard_errors(covariance_from_design(design, residuals, 1)) or [None])[0]
    mean_force = float(np.mean(force))
    mean_power = float(np.mean(effective_wheel_power(force, filtered["speed_ms"].to_numpy())))
    lo, hi = confidence_interval(mean_force, se, float(config.get("fitting", {}).get("confidence_level", 0.95)))
    status = evaluate_status(diagnostics, model_cfg, {"drive_force": mean_force})
    params = [
        PhysicsParameterEstimate(parameter_name="effective_drive_force", value=mean_force, unit="N", standard_error=se, confidence_interval_low=lo, confidence_interval_high=hi, sample_count=len(filtered), model_name=LONGITUDINAL_MODEL_NAME, model_version=LONGITUDINAL_MODEL_VERSION, status=status),
        PhysicsParameterEstimate(parameter_name="effective_wheel_power", value=mean_power, unit="W", sample_count=len(filtered), model_name=LONGITUDINAL_MODEL_NAME, model_version=LONGITUDINAL_MODEL_VERSION, status=status),
        PhysicsParameterEstimate(parameter_name="rolling_resistance_coefficient", value=crr, unit="dimensionless", sample_count=len(filtered), model_name=LONGITUDINAL_MODEL_NAME, model_version=LONGITUDINAL_MODEL_VERSION, status=status, provenance="assumed"),
    ]
    return PhysicsModelResult(
        model_name=LONGITUDINAL_MODEL_NAME,
        model_version=LONGITUDINAL_MODEL_VERSION,
        parameters=params,
        diagnostics=diagnostics,
        identifiability=ident,
        status=status,
        predictions=_records(filtered, prediction, "effective_drive_force_mean_predicted"),
        residuals=_records(filtered, residuals, "effective_drive_force_residual"),
    )


def _filter(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, int]]:
    mask = np.isfinite(pd.to_numeric(df["speed_ms"], errors="coerce")) & np.isfinite(pd.to_numeric(df["acceleration_longitudinal"], errors="coerce"))
    reasons = {"non_finite_required": int((~mask).sum())}
    out = df.loc[mask].copy()
    start = len(out)
    out = out[out["speed_ms"] >= float(config.get("filtering", {}).get("min_speed_ms", 20.0))]
    reasons["below_min_speed"] = start - len(out)
    if "throttle_percent" in out.columns:
        start = len(out)
        out = out[out["throttle_percent"] >= float(config.get("filtering", {}).get("full_throttle_threshold", 95.0))]
        reasons["not_full_throttle"] = start - len(out)
    if "brake_active" in out.columns and bool(config.get("filtering", {}).get("exclude_braking", True)):
        start = len(out)
        out = out[~out["brake_active"].astype(bool)]
        reasons["braking"] = start - len(out)
    return out, {k: int(v) for k, v in reasons.items() if v}


def _records(df: pd.DataFrame, values: np.ndarray, value_name: str) -> list[dict[str, Any]]:
    cols = [c for c in ("time", "lap_number", "distance", "speed_ms") if c in df.columns]
    out = df[cols].copy() if cols else pd.DataFrame(index=df.index)
    out["model"] = value_name
    out["value"] = values
    return out.replace({np.nan: None}).to_dict(orient="records")


def _insufficient(rows: int, warning: str, ident: IdentifiabilityReport, reasons: dict[str, int] | None = None, used: int = 0) -> PhysicsModelResult:
    result = PhysicsModelResult(model_name=LONGITUDINAL_MODEL_NAME, model_version=LONGITUDINAL_MODEL_VERSION, identifiability=ident, status="insufficient_data")
    result.diagnostics.rows_input = rows
    result.diagnostics.rows_used = used
    result.diagnostics.rows_excluded = max(rows - used, 0)
    result.diagnostics.exclusion_reasons = reasons or {}
    result.diagnostics.warnings = [warning]
    return result
