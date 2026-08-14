from __future__ import annotations

import numpy as np


def drag_force(speed_ms: np.ndarray | float, *, air_density: float, effective_drag_parameter: float) -> np.ndarray:
    """Return F_drag = 0.5 * rho * CdA * v^2 in Newtons.

    ``effective_drag_parameter`` is CdA. Cd and frontal area are not
    separately identifiable from telemetry without independent information.
    """
    return 0.5 * air_density * effective_drag_parameter * np.asarray(speed_ms, dtype=float) ** 2


def estimate_cda_from_coast(speed_ms: np.ndarray, acceleration_ms2: np.ndarray, *, air_density: float, mass_kg: float) -> tuple[float, np.ndarray]:
    y = -mass_kg * np.asarray(acceleration_ms2, dtype=float)
    x = 0.5 * air_density * np.asarray(speed_ms, dtype=float) ** 2
    design = x.reshape(-1, 1)
    estimate = float(np.linalg.lstsq(design, y, rcond=None)[0][0])
    return estimate, design
