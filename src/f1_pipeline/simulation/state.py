"""Simulation state representation.

Defines the explicit mutable state of a simulation during a single run.
State transitions should be deterministic given current state, parameters,
scenario, and random seed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from f1_pipeline.simulation.schemas import CompoundName


@dataclass
class SimulationState:
    lap: int = 0
    distance_m: float = 0.0
    elapsed_time_s: float = 0.0
    
    fuel_mass_kg: float = 0.0
    vehicle_mass_kg: float = 0.0
    
    tyre_compound: str = "UNKNOWN"
    tyre_age: int = 0
    tyre_grip_multiplier: float = 1.0
    
    track_grip_multiplier: float = 1.0
    
    air_temperature_c: float = 0.0
    track_temperature_c: float = 0.0
    rainfall_mm: float = 0.0
    
    pit_status: bool = False
    
    def copy(self) -> SimulationState:
        """Create a deep copy of the state."""
        return SimulationState(
            lap=self.lap,
            distance_m=self.distance_m,
            elapsed_time_s=self.elapsed_time_s,
            fuel_mass_kg=self.fuel_mass_kg,
            vehicle_mass_kg=self.vehicle_mass_kg,
            tyre_compound=self.tyre_compound,
            tyre_age=self.tyre_age,
            tyre_grip_multiplier=self.tyre_grip_multiplier,
            track_grip_multiplier=self.track_grip_multiplier,
            air_temperature_c=self.air_temperature_c,
            track_temperature_c=self.track_temperature_c,
            rainfall_mm=self.rainfall_mm,
            pit_status=self.pit_status,
        )
