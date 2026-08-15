"""Simulation scenario definition and validation.

A scenario is an immutable configuration that specifies what is to be simulated.
It serves as the input to the Layer 4 Simulation Engine.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from f1_pipeline.core.hashing import file_sha256
from f1_pipeline.simulation.schemas import CompoundName


class TyreStintSpec(BaseModel):
    compound: CompoundName
    start_lap: int
    end_lap: int


class PitStopSpec(BaseModel):
    lap: int
    pit_loss_seconds: float | None = None
    change_compound_to: CompoundName | None = None


class WeatherSpec(BaseModel):
    air_temperature_c: float | None = None
    track_temperature_c: float | None = None
    rainfall_mm: float = 0.0


class Scenario(BaseModel):
    season: int
    event: str
    session_type: str
    driver_code: str

    total_laps: int
    starting_fuel_kg: float | None = None

    tyre_strategy: list[TyreStintSpec] = Field(default_factory=list)
    pit_stops: list[PitStopSpec] = Field(default_factory=list)
    weather: WeatherSpec = Field(default_factory=WeatherSpec)

    def scenario_hash(self) -> str:
        """Calculate a deterministic hash of the scenario."""
        # Convert to dictionary and serialize to JSON with sorted keys
        data = self.model_dump(mode="json")
        json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        import hashlib
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def validate_scenario(self) -> list[str]:
        """Validate structural and physical plausibility of the scenario."""
        warnings = []
        if self.total_laps <= 0:
            raise ValueError("total_laps must be > 0")
        
        if self.starting_fuel_kg is not None and self.starting_fuel_kg < 0:
            raise ValueError("starting_fuel_kg cannot be negative")

        # Validate tyre strategy covers the entire race (if provided)
        if self.tyre_strategy:
            # Sort by start lap
            sorted_stints = sorted(self.tyre_strategy, key=lambda s: s.start_lap)
            if sorted_stints[0].start_lap != 1:
                warnings.append("Tyre strategy does not start at lap 1.")
            
            # Check for gaps/overlaps
            current_lap = sorted_stints[0].end_lap
            for stint in sorted_stints[1:]:
                if stint.start_lap != current_lap + 1:
                    warnings.append(f"Tyre strategy gap or overlap between lap {current_lap} and {stint.start_lap}.")
                current_lap = stint.end_lap
            
            if current_lap < self.total_laps:
                warnings.append(f"Tyre strategy only covers up to lap {current_lap}, but total_laps is {self.total_laps}.")
            if current_lap > self.total_laps:
                warnings.append(f"Tyre strategy covers up to lap {current_lap}, which exceeds total_laps {self.total_laps}.")
        
        # Validate pit stops match tyre strategy transitions
        pit_laps = {stop.lap for stop in self.pit_stops}
        strategy_transitions = {stint.start_lap - 1 for stint in self.tyre_strategy if stint.start_lap > 1}
        
        for transition in strategy_transitions:
            if transition not in pit_laps:
                warnings.append(f"Tyre strategy indicates a compound change after lap {transition}, but no pit stop is scheduled.")

        return warnings


def load_scenario(path: str | Path) -> Scenario:
    """Load a Scenario from a JSON file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {file_path}")
    
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        
    return Scenario.model_validate(data)
