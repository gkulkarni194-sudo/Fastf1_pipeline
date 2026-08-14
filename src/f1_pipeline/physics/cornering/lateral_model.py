from __future__ import annotations

import numpy as np


def lateral_acceleration_from_radius(speed_ms: np.ndarray | float, radius_m: np.ndarray | float) -> np.ndarray:
    radius = np.asarray(radius_m, dtype=float)
    return np.asarray(speed_ms, dtype=float) ** 2 / radius


def infer_corner_radius(speed_ms: np.ndarray | float, lateral_acceleration_ms2: np.ndarray | float) -> np.ndarray:
    accel = np.asarray(lateral_acceleration_ms2, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        radius = np.asarray(speed_ms, dtype=float) ** 2 / np.abs(accel)
    radius[~np.isfinite(radius)] = np.nan
    return radius
