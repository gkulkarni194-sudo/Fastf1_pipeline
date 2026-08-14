from __future__ import annotations

from typing import Any

import numpy as np

from f1_pipeline.physics.schemas import PhysicsDiagnostics


def regression_diagnostics(
    observed: np.ndarray,
    predicted: np.ndarray,
    *,
    rows_input: int,
    exclusion_reasons: dict[str, int] | None = None,
    convergence_status: str = "converged",
) -> PhysicsDiagnostics:
    observed = np.asarray(observed, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = np.isfinite(observed) & np.isfinite(predicted)
    observed = observed[mask]
    predicted = predicted[mask]
    residuals = observed - predicted
    n = int(len(residuals))
    reasons = exclusion_reasons or {}
    if n == 0:
        return PhysicsDiagnostics(
            sample_count=0,
            rows_input=rows_input,
            rows_used=0,
            rows_excluded=rows_input,
            exclusion_reasons=reasons,
            convergence_status=convergence_status,
        )
    sse = float(np.sum(residuals ** 2))
    centered = observed - float(np.mean(observed))
    sst = float(np.sum(centered ** 2))
    r2 = None if sst <= 0 else float(1.0 - sse / sst)
    return PhysicsDiagnostics(
        rmse=float(np.sqrt(np.mean(residuals ** 2))),
        mae=float(np.mean(np.abs(residuals))),
        r_squared=r2,
        sample_count=n,
        residual_mean=float(np.mean(residuals)),
        residual_std=float(np.std(residuals, ddof=1)) if n > 1 else 0.0,
        convergence_status=convergence_status,
        rows_input=rows_input,
        rows_used=n,
        rows_excluded=max(rows_input - n, 0),
        exclusion_reasons=reasons,
        warnings=_diagnostic_warnings(residuals),
    )


def evaluate_status(diagnostics: PhysicsDiagnostics, config: dict[str, Any], parameter_values: dict[str, float] | None = None) -> str:
    min_samples = int(config.get("min_samples", 0))
    if diagnostics.sample_count < min_samples:
        return "insufficient_data"
    if diagnostics.convergence_status not in {"converged", "solved"}:
        return "failed"
    warnings: list[str] = []
    max_rmse = config.get("max_rmse")
    if max_rmse is not None and diagnostics.rmse is not None and diagnostics.rmse > float(max_rmse):
        warnings.append("rmse_above_threshold")
    min_r2 = config.get("minimum_r_squared")
    if min_r2 is not None and diagnostics.r_squared is not None and diagnostics.r_squared < float(min_r2):
        warnings.append("r_squared_below_threshold")
    for name, value in (parameter_values or {}).items():
        bounds = config.get(f"{name}_bounds")
        if isinstance(bounds, list) and len(bounds) == 2 and not (float(bounds[0]) <= value <= float(bounds[1])):
            return "rejected"
    return "warning" if warnings else "accepted"


def _diagnostic_warnings(residuals: np.ndarray) -> list[str]:
    if len(residuals) < 3:
        return []
    warnings = []
    std = float(np.std(residuals))
    if std > 0 and int(np.sum(np.abs(residuals - np.mean(residuals)) > 4.0 * std)) > 0:
        warnings.append("extreme_residuals_detected")
    first = float(np.mean(residuals[: max(1, len(residuals) // 3)]))
    last = float(np.mean(residuals[-max(1, len(residuals) // 3) :]))
    if std > 0 and abs(first - last) > std:
        warnings.append("possible_systematic_residual_pattern")
    return warnings
