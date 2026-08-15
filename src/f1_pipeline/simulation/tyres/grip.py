"""Tyre grip model."""
from __future__ import annotations

from typing import Any

from f1_pipeline.simulation.schemas import FallbackRecord
from f1_pipeline.simulation.tyres.state import TyreState


class TyreGripModel:
    """Models absolute grip levels of different tyre compounds."""

    def __init__(self, config: dict[str, Any], layer3_params: dict[str, Any] | None = None):
        self.config = config.get("tyres", {})
        self.compounds_config = self.config.get("compounds", {})
        self.layer3_params = layer3_params or {}
        self.fallbacks: list[FallbackRecord] = []
        
        self.base_grips: dict[str, float] = {}
        self.grip_sensitivity = float(self.config.get("grip_lap_time_sensitivity", 0.3))
        
        for compound, comp_cfg in self.compounds_config.items():
            grip = float(comp_cfg.get("base_grip_multiplier", 1.0))
            self.base_grips[compound] = grip
            
            self.fallbacks.append(FallbackRecord(
                parameter=f"base_grip_{compound}",
                source="configured_fallback",
                value=grip,
                reason="Layer 3 per-compound absolute grip unavailable"
            ))
            
    def get_base_grip(self, compound: str) -> float:
        """Get the base grip multiplier for a compound."""
        return self.base_grips.get(compound, self.base_grips.get("MEDIUM", 1.0))
        
    def grip_lap_time_effect(self, state: TyreState) -> float:
        """Calculate the lap time effect from base compound grip differences."""
        # A multiplier of 1.0 means no adjustment.
        # A multiplier of 0.97 means 3% less grip, which translates to a lap time penalty.
        # This is separate from degradation with age.
        base_grip = self.get_base_grip(state.compound)
        
        # Grip multiplier > 1 means faster, < 1 means slower.
        # We want to return a lap time multiplier.
        # E.g., if grip is 0.97, lap time multiplier is > 1.0.
        # Simplified model: lap_time_mult = 1.0 + (1.0 - grip) * sensitivity
        lap_time_mult = 1.0 + (1.0 - base_grip) * self.grip_sensitivity
        
        return lap_time_mult
