from __future__ import annotations


def rolling_resistance_force(*, rolling_resistance_coefficient: float, mass_kg: float, gravity: float) -> float:
    return float(rolling_resistance_coefficient * mass_kg * gravity)
