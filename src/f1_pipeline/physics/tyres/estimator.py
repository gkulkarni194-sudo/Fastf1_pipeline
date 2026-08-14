from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from f1_pipeline.physics.constants import constant_from_config
from f1_pipeline.physics.diagnostics import evaluate_status, regression_diagnostics
from f1_pipeline.physics.schemas import IdentifiabilityReport, PhysicsModelResult, PhysicsParameterEstimate
from f1_pipeline.physics.tyres.degradation_model import fit_linear_degradation
from f1_pipeline.physics.tyres.grip_model import effective_grip_coefficient
from f1_pipeline.physics.uncertainty import confidence_interval, covariance_from_design, standard_errors


TYRE_MODEL_NAME = "controlled_linear_tyre_degradation"
TYRE_MODEL_VERSION = "1.0"
GRIP_MODEL_NAME = "effective_lateral_grip_proxy"
GRIP_MODEL_VERSION = "1.0"


def estimate_tyre_degradation(laps: pd.DataFrame, config: dict[str, Any]) -> PhysicsModelResult:
    model_cfg = config.get("models", {}).get("tyres", {})
    ident = IdentifiabilityReport(
        identifiable_parameters=["estimated_degradation_coefficient"],
        non_identifiable_parameters=["causal_tyre_degradation", "compound_intrinsic_degradation"],
        assumptions=["Available lap-level controls proxy confounding from fuel load, traffic, DRS, braking and track state when present."],
        limitations=["Coefficient is descriptive unless upstream data provides adequate controls."],
    )
    age_col = _first(laps, ["tyre_age", "tyre_life", "lap_age", "lap_number"])
    time_col = _first(laps, ["lap_time_seconds", "lap_time"])
    if age_col is None or time_col is None:
        return _insufficient(TYRE_MODEL_NAME, TYRE_MODEL_VERSION, len(laps), "missing tyre age or lap time", ident)
    df = laps.copy()
    if time_col == "lap_time" and pd.api.types.is_timedelta64_dtype(df[time_col]):
        y = df[time_col].dt.total_seconds()
    else:
        y = pd.to_numeric(df[time_col], errors="coerce")
    age = pd.to_numeric(df[age_col], errors="coerce")
    candidate_controls = [c for c in ["lap_number", "average_speed", "throttle_fraction", "brake_fraction", "DRS_fraction", "track_status"] if c in df.columns and c != age_col]
    numeric = [age.rename("age"), y.rename("lap_time_seconds")]
    for col in candidate_controls:
        numeric.append(pd.to_numeric(df[col], errors="coerce").rename(col))
    data = pd.concat(numeric, axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) < int(model_cfg.get("min_samples", 0)):
        return _insufficient(TYRE_MODEL_NAME, TYRE_MODEL_VERSION, len(laps), "too few controlled lap samples", ident, {"non_finite_or_missing": len(laps) - len(data)}, len(data))
    controls = _identifiable_controls(data, candidate_controls)
    control_matrix = data[controls].to_numpy() if controls else None
    beta, design = fit_linear_degradation(data["age"].to_numpy(), data["lap_time_seconds"].to_numpy(), control_matrix)
    predicted = design @ beta
    residuals = data["lap_time_seconds"].to_numpy() - predicted
    diagnostics = regression_diagnostics(data["lap_time_seconds"].to_numpy(), predicted, rows_input=len(laps), exclusion_reasons={"non_finite_or_missing": len(laps) - len(data)})
    se = (standard_errors(covariance_from_design(design, residuals, len(beta))) or [None, None])[1]
    value = float(beta[1])
    lo, hi = confidence_interval(value, se, float(config.get("fitting", {}).get("confidence_level", 0.95)))
    status = evaluate_status(diagnostics, model_cfg, {"degradation": value})
    return PhysicsModelResult(
        model_name=TYRE_MODEL_NAME,
        model_version=TYRE_MODEL_VERSION,
        parameters=[PhysicsParameterEstimate(parameter_name="estimated_degradation_coefficient", value=value, unit="s/lap_age", standard_error=se, confidence_interval_low=lo, confidence_interval_high=hi, sample_count=len(data), model_name=TYRE_MODEL_NAME, model_version=TYRE_MODEL_VERSION, status=status)],
        diagnostics=diagnostics,
        identifiability=ident,
        status=status,
        predictions=_records(data, predicted, "lap_time_predicted"),
        residuals=_records(data, residuals, "lap_time_residual"),
    )


def estimate_tyre_grip(telemetry: pd.DataFrame, config: dict[str, Any]) -> PhysicsModelResult:
    ident = IdentifiabilityReport(
        identifiable_parameters=["effective_grip_parameter"],
        non_identifiable_parameters=["true_tyre_mu", "aero_load_independent_grip"],
        assumptions=["Peak observed lateral acceleration is a descriptive grip proxy."],
        limitations=["Aerodynamic downforce, track banking, kerbs and driver margin are not separated."],
    )
    if "acceleration_lateral" not in telemetry.columns:
        return _insufficient(GRIP_MODEL_NAME, GRIP_MODEL_VERSION, len(telemetry), "missing acceleration_lateral", ident)
    g = constant_from_config(config, "gravity").value
    values = effective_grip_coefficient(pd.to_numeric(telemetry["acceleration_lateral"], errors="coerce").to_numpy(), gravity=g)
    values = values[np.isfinite(values)]
    if len(values) < int(config.get("models", {}).get("cornering", {}).get("min_samples", 0)):
        return _insufficient(GRIP_MODEL_NAME, GRIP_MODEL_VERSION, len(telemetry), "too few lateral acceleration samples", ident, {"non_finite_or_missing": len(telemetry) - len(values)}, len(values))
    grip = float(np.nanpercentile(values, 95))
    status = "accepted"
    return PhysicsModelResult(
        model_name=GRIP_MODEL_NAME,
        model_version=GRIP_MODEL_VERSION,
        parameters=[PhysicsParameterEstimate(parameter_name="effective_grip_parameter", value=grip, unit="dimensionless", sample_count=len(values), model_name=GRIP_MODEL_NAME, model_version=GRIP_MODEL_VERSION, status=status)],
        identifiability=ident,
        status=status,
    )


def _first(df: pd.DataFrame, names: list[str]) -> str | None:
    return next((name for name in names if name in df.columns), None)


def _identifiable_controls(data: pd.DataFrame, controls: list[str]) -> list[str]:
    usable: list[str] = []
    age = data["age"].to_numpy(dtype=float)
    for col in controls:
        values = data[col].to_numpy(dtype=float)
        if np.nanstd(values) <= 0:
            continue
        corr = np.corrcoef(age, values)[0, 1]
        if np.isfinite(corr) and abs(corr) >= 0.98:
            continue
        usable.append(col)
    return usable


def _records(df: pd.DataFrame, values: np.ndarray, value_name: str) -> list[dict[str, Any]]:
    out = pd.DataFrame({"model": value_name, "value": values})
    if "lap_number" in df.columns:
        out["lap_number"] = df["lap_number"].to_numpy()
    return out.replace({np.nan: None}).to_dict(orient="records")


def _insufficient(name: str, version: str, rows: int, warning: str, ident: IdentifiabilityReport, reasons: dict[str, int] | None = None, used: int = 0) -> PhysicsModelResult:
    result = PhysicsModelResult(model_name=name, model_version=version, identifiability=ident, status="insufficient_data")
    result.diagnostics.rows_input = rows
    result.diagnostics.rows_used = used
    result.diagnostics.rows_excluded = max(rows - used, 0)
    result.diagnostics.exclusion_reasons = reasons or {}
    result.diagnostics.warnings = [warning]
    return result
