from __future__ import annotations

from statistics import NormalDist

import numpy as np


def covariance_from_design(x: np.ndarray, residuals: np.ndarray, parameter_count: int) -> np.ndarray | None:
    if x.ndim != 2 or len(residuals) <= parameter_count:
        return None
    xtx = x.T @ x
    try:
        inv = np.linalg.inv(xtx)
    except np.linalg.LinAlgError:
        return None
    sigma2 = float((residuals @ residuals) / (len(residuals) - parameter_count))
    return inv * sigma2


def standard_errors(covariance: np.ndarray | None) -> list[float | None]:
    if covariance is None:
        return []
    diag = np.diag(covariance)
    if np.any(diag < 0) or np.any(~np.isfinite(diag)):
        return [None for _ in diag]
    return [float(v) for v in np.sqrt(diag)]


def confidence_interval(value: float | None, standard_error: float | None, confidence_level: float) -> tuple[float | None, float | None]:
    if value is None or standard_error is None or not np.isfinite(value) or not np.isfinite(standard_error):
        return None, None
    z = NormalDist().inv_cdf(0.5 + confidence_level / 2.0)
    return float(value - z * standard_error), float(value + z * standard_error)
