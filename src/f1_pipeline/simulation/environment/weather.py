"""Weather simulation model."""
from __future__ import annotations

from typing import Any

from f1_pipeline.simulation.scenario import WeatherSpec
from f1_pipeline.simulation.state import SimulationState


class WeatherModel:
    """Models weather conditions and their effects."""

    def __init__(self, config: dict[str, Any]):
        self.config = config.get("weather", {})
        self.rain_penalty_fraction = float(self.config.get("rain_lap_time_penalty_fraction", 0.08))
        self.temp_sensitivity = float(self.config.get("temperature_sensitivity_per_degree_c", 0.005))
        
        self.default_air_temp = float(self.config.get("default_air_temperature_c", 25.0))
        self.default_track_temp = float(self.config.get("default_track_temperature_c", 35.0))

    def initialize_state(self, state: SimulationState, weather_spec: WeatherSpec) -> None:
        """Initialize weather variables in the simulation state."""
        state.air_temperature_c = weather_spec.air_temperature_c if weather_spec.air_temperature_c is not None else self.default_air_temp
        state.track_temperature_c = weather_spec.track_temperature_c if weather_spec.track_temperature_c is not None else self.default_track_temp
        state.rainfall_mm = weather_spec.rainfall_mm

    def update_state(self, state: SimulationState) -> None:
        """Update weather state for the next lap. 
        Currently implements a static weather model.
        """
        pass # Static weather for now

    def weather_lap_time_adjustment(self, state: SimulationState, base_lap_time: float) -> float:
        """Calculate lap time adjustment multiplier due to weather."""
        multiplier = 1.0
        
        # Rain penalty
        if state.rainfall_mm > 0:
            # Simple linear model: full penalty at 5mm rain
            rain_factor = min(1.0, state.rainfall_mm / 5.0)
            multiplier += rain_factor * self.rain_penalty_fraction
            
        # Temperature effect (optimal temp assumed to be 40C track)
        temp_diff = state.track_temperature_c - 40.0
        # Slightly slower if too hot or too cold
        multiplier += abs(temp_diff) * self.temp_sensitivity
            
        return multiplier
