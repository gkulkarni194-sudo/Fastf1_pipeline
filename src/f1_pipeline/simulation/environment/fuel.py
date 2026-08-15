"""Fuel simulation model."""
from __future__ import annotations

from typing import Any

import numpy as np


class FuelModel:
    """Models fuel consumption and its effect on lap time."""

    def __init__(self, config: dict[str, Any], seed: int | None = None):
        self.config = config.get("fuel", {})
        self.consumption_per_lap_kg = float(self.config.get("consumption_per_lap_kg", 1.5))
        self.lap_time_effect_per_kg = float(self.config.get("lap_time_effect_per_kg", 0.035))
        self.consumption_stdev_kg = float(self.config.get("consumption_stdev_kg", 0.0))
        self.rng = np.random.default_rng(seed)

    def fuel_mass_after_lap(self, current_fuel_kg: float, stochastic: bool = False) -> float:
        """Calculate fuel mass after completing one lap."""
        if stochastic and self.consumption_stdev_kg > 0:
            burn = self.rng.normal(self.consumption_per_lap_kg, self.consumption_stdev_kg)
            burn = max(0.0, burn)  # Cannot gain fuel
        else:
            burn = self.consumption_per_lap_kg
            
        remaining = current_fuel_kg - burn
        return max(0.0, remaining)

    def fuel_lap_time_effect(self, fuel_mass_kg: float) -> float:
        """Calculate the lap time penalty due to fuel mass."""
        return fuel_mass_kg * self.lap_time_effect_per_kg
