from __future__ import annotations

import numpy as np


def effective_grip_coefficient(lateral_acceleration_ms2: np.ndarray, *, gravity: float) -> np.ndarray:
    return np.abs(np.asarray(lateral_acceleration_ms2, dtype=float)) / gravity
