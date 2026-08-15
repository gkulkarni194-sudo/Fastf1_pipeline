"""Track evolution simulation model."""
from __future__ import annotations

from typing import Any

from f1_pipeline.simulation.state import SimulationState


class TrackEvolutionModel:
    """Models how the track grip changes over the course of a session."""

    def __init__(self, config: dict[str, Any]):
        self.config = config.get("track", {})
        self.evolution_model = self.config.get("evolution_model", "linear")
        self.evolution_rate = float(self.config.get("evolution_rate_per_lap", -0.005)) # Negative means faster
        self.baseline_grip = float(self.config.get("baseline_grip_multiplier", 1.0))

    def initialize_state(self, state: SimulationState) -> None:
        """Initialize track grip in the simulation state."""
        state.track_grip_multiplier = self.baseline_grip

    def update_state(self, state: SimulationState) -> None:
        """Update track grip for the current lap."""
        if self.evolution_model == "linear":
            # Track gets faster (lower multiplier) as rubber is laid down
            # Using max to prevent unrealistic infinite evolution
            evolution_effect = self.evolution_rate * state.lap
            state.track_grip_multiplier = max(0.9, self.baseline_grip + evolution_effect)
        else:
            # Fallback to static
            state.track_grip_multiplier = self.baseline_grip
