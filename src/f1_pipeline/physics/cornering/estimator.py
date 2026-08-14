from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from f1_pipeline.physics.cornering.lateral_model import lateral_acceleration_from_radius
from f1_pipeline.physics.diagnostics import evaluate_status, regression_diagnostics
from f1_pipeline.physics.schemas import IdentifiabilityReport, PhysicsModelResult, PhysicsParameterEstimate


CORNERING_MODEL_NAME = "lateral_acceleration_radius_consistency"
CORNERING_MODEL_VERSION = "1.0"


def estimate_cornering(corners: pd.DataFrame, telemetry: pd.DataFrame | None, config: dict[str, Any]) -> PhysicsModelResult:
    model_cfg = config.get("models", {}).get("cornering", {})
    ident = IdentifiabilityReport(
        identifiable_parameters=["effective_corner_radius", "lateral_acceleration_consistency"],
        non_identifiable_parameters=["true_track_radius", "true_tyre_mu"],
        assumptions=["Corner radius must be provided by Layer 2 or inferable from speed and lateral acceleration samples."],
        limitations=["Layer 2 heuristic corner indices are not official FIA corner numbers."],
    )
    if corners.empty and (telemetry is None or telemetry.empty):
        return _insufficient(0, "no corner or telemetry data", ident)

    if {"corner_radius", "minimum_corner_speed", "peak_lateral_acceleration"}.issubset(corners.columns):
        df = corners.replace([np.inf, -np.inf], np.nan).dropna(subset=["corner_radius", "minimum_corner_speed", "peak_lateral_acceleration"]).copy()
        speed = pd.to_numeric(df["minimum_corner_speed"], errors="coerce").to_numpy(dtype=float) / 3.6
        radius = pd.to_numeric(df["corner_radius"], errors="coerce").to_numpy(dtype=float)
        observed = np.abs(pd.to_numeric(df["peak_lateral_acceleration"], errors="coerce").to_numpy(dtype=float))
    elif telemetry is not None and {"speed_ms", "acceleration_lateral"}.issubset(telemetry.columns):
        df = telemetry.replace([np.inf, -np.inf], np.nan).dropna(subset=["speed_ms", "acceleration_lateral"]).copy()
        df = df[np.abs(df["acceleration_lateral"]) > 1.0]
        if len(df) < int(model_cfg.get("min_samples", 0)):
            return _insufficient(len(telemetry), "corner radius unavailable and too few lateral telemetry samples", ident, {"non_corner_or_missing": len(telemetry) - len(df)}, len(df))
        speed = df["speed_ms"].to_numpy(dtype=float)
        observed = np.abs(df["acceleration_lateral"].to_numpy(dtype=float))
        radius = speed**2 / observed
    else:
        return _insufficient(len(corners), "corner radius and lateral telemetry unavailable", ident)

    mask = np.isfinite(speed) & np.isfinite(radius) & np.isfinite(observed) & (radius > 0)
    speed, radius, observed = speed[mask], radius[mask], observed[mask]
    if len(speed) < int(model_cfg.get("min_samples", 0)):
        return _insufficient(len(corners), "too few valid cornering samples", ident, {"non_finite_or_invalid_radius": int((~mask).sum())}, len(speed))
    predicted = lateral_acceleration_from_radius(speed, radius)
    residuals = observed - predicted
    rows_input = len(corners) if not corners.empty else (len(telemetry) if telemetry is not None else 0)
    diagnostics = regression_diagnostics(observed, predicted, rows_input=rows_input, exclusion_reasons={"non_finite_or_invalid_radius": int((~mask).sum())})
    mean_radius = float(np.nanmedian(radius))
    status = evaluate_status(diagnostics, model_cfg, {"grip": float(np.nanpercentile(observed / 9.80665, 95))})
    return PhysicsModelResult(
        model_name=CORNERING_MODEL_NAME,
        model_version=CORNERING_MODEL_VERSION,
        parameters=[
            PhysicsParameterEstimate(parameter_name="effective_corner_radius", value=mean_radius, unit="m", sample_count=len(speed), model_name=CORNERING_MODEL_NAME, model_version=CORNERING_MODEL_VERSION, status=status),
            PhysicsParameterEstimate(parameter_name="lateral_acceleration_consistency_rmse", value=diagnostics.rmse, unit="m/s^2", sample_count=len(speed), model_name=CORNERING_MODEL_NAME, model_version=CORNERING_MODEL_VERSION, status=status),
        ],
        diagnostics=diagnostics,
        identifiability=ident,
        status=status,
        predictions=pd.DataFrame({"model": "lateral_acceleration_predicted", "value": predicted}).replace({np.nan: None}).to_dict(orient="records"),
        residuals=pd.DataFrame({"model": "lateral_acceleration_residual", "value": residuals}).replace({np.nan: None}).to_dict(orient="records"),
    )


def _insufficient(rows: int, warning: str, ident: IdentifiabilityReport, reasons: dict[str, int] | None = None, used: int = 0) -> PhysicsModelResult:
    result = PhysicsModelResult(model_name=CORNERING_MODEL_NAME, model_version=CORNERING_MODEL_VERSION, identifiability=ident, status="insufficient_data")
    result.diagnostics.rows_input = rows
    result.diagnostics.rows_used = used
    result.diagnostics.rows_excluded = max(rows - used, 0)
    result.diagnostics.exclusion_reasons = reasons or {}
    result.diagnostics.warnings = [warning]
    return result
