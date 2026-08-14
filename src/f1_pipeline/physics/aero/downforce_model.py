from __future__ import annotations

import numpy as np


def downforce(speed_ms: np.ndarray | float, *, air_density: float, effective_downforce_parameter: float) -> np.ndarray:
    """Return F_downforce = 0.5 * rho * ClA * v^2 in Newtons."""
    return 0.5 * air_density * effective_downforce_parameter * np.asarray(speed_ms, dtype=float) ** 2


def estimate_cla_from_lateral_capacity(
    speed_ms: np.ndarray,
    lateral_acceleration_ms2: np.ndarray,
    *,
    air_density: float,
    mass_kg: float,
    gravity: float,
) -> tuple[float, np.ndarray]:
    """Estimate an effective ClA under a friction-limited cornering assumption.

    This is only identifiable as an effective parameter when lateral
    acceleration observations reach a grip envelope. It must not be
    interpreted as true aerodynamic Cl or independent area.
    """
    normal_force_proxy = mass_kg * (np.abs(lateral_acceleration_ms2) - gravity)
    x = 0.5 * air_density * np.asarray(speed_ms, dtype=float) ** 2
    design = x.reshape(-1, 1)
    estimate = float(np.linalg.lstsq(design, normal_force_proxy, rcond=None)[0][0])
    return estimate, design
