from __future__ import annotations

import numpy as np


def fit_linear_degradation(tyre_age: np.ndarray, lap_time_seconds: np.ndarray, controls: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    age = np.asarray(tyre_age, dtype=float)
    y = np.asarray(lap_time_seconds, dtype=float)
    if controls is None:
        x = np.column_stack([np.ones(len(age)), age])
    else:
        x = np.column_stack([np.ones(len(age)), age, np.asarray(controls, dtype=float)])
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    return beta, x
