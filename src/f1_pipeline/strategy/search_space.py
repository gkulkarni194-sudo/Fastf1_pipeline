"""Search space definition for strategy optimization."""
from __future__ import annotations

from pydantic import BaseModel, Field


class StopsSpace(BaseModel):
    min: int
    max: int


class PitWindowSpace(BaseModel):
    min_lap: int
    max_lap: int


class SearchSpace(BaseModel):
    driver_code: str
    total_laps: int
    compounds: list[str]
    stops: StopsSpace
    stint_min_laps: int
    
    # Optional bounds for the entire pit window (e.g., no stops before lap 5, no stops after lap 50)
    pit_windows: PitWindowSpace | None = None
    
    def validate_space(self) -> list[str]:
        """Check if the search space is logically sound."""
        warnings = []
        if self.stops.max < self.stops.min:
            warnings.append("stops.max cannot be less than stops.min")
            
        if self.stops.min < 0:
            warnings.append("stops.min cannot be less than 0")
            
        if not self.compounds:
            warnings.append("At least one compound must be available")
            
        if self.stint_min_laps < 1:
            warnings.append("stint_min_laps must be at least 1")
            
        # Check if race is long enough to support min stops given min stint lengths
        required_laps = (self.stops.min + 1) * self.stint_min_laps
        if required_laps > self.total_laps:
            warnings.append(f"Race too short for {self.stops.min} stops with {self.stint_min_laps} min laps per stint")
            
        if self.pit_windows:
            if self.pit_windows.max_lap < self.pit_windows.min_lap:
                warnings.append("pit_windows.max_lap cannot be less than min_lap")
            if self.pit_windows.min_lap < 1:
                warnings.append("pit_windows.min_lap cannot be less than 1")
            if self.pit_windows.max_lap >= self.total_laps:
                warnings.append("pit_windows.max_lap should be less than total_laps")
                
        return warnings
