from __future__ import annotations

import numpy as np


def longitudinal_force_balance(
    acceleration_ms2: np.ndarray | float,
    *,
    mass_kg: float,
    drag_force_n: np.ndarray | float = 0.0,
    rolling_force_n: np.ndarray | float = 0.0,
) -> np.ndarray:
    """Return effective drive force from m*a + drag + rolling.

    This is an effective wheel-force proxy. It does not identify engine
    power, drivetrain efficiency, or losses independently.
    """
    return mass_kg * np.asarray(acceleration_ms2, dtype=float) + np.asarray(drag_force_n) + np.asarray(rolling_force_n)


def effective_wheel_power(force_n: np.ndarray | float, speed_ms: np.ndarray | float) -> np.ndarray:
    return np.asarray(force_n, dtype=float) * np.asarray(speed_ms, dtype=float)
