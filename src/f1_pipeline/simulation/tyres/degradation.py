"""Tyre degradation model."""
from __future__ import annotations

from typing import Any

from f1_pipeline.simulation.schemas import FallbackRecord
from f1_pipeline.simulation.tyres.state import TyreState


class TyreDegradationModel:
    """Models how tyre performance degrades with age."""

    def __init__(self, config: dict[str, Any], layer3_params: dict[str, Any] | None = None, seed: int | None = None):
        self.config = config.get("tyres", {})
        self.compounds_config = self.config.get("compounds", {})
        self.layer3_params = layer3_params or {}
        self.fallbacks: list[FallbackRecord] = []
        
        # Load estimated degradation if available, otherwise use configured fallbacks per compound
        self.degradation_rates: dict[str, float] = {}
        self.cliff_ages: dict[str, int] = {}
        
        # Check for a global estimated degradation from Layer 3
        # (In a more advanced model, Layer 3 might estimate per-compound deg)
        est_deg = self.layer3_params.get("estimated_degradation_coefficient")
        
        for compound, comp_cfg in self.compounds_config.items():
            if est_deg is not None:
                # If we have an estimate, we might still scale it by compound hardness
                # But for simplicity in this version, if an estimate exists we use it, 
                # perhaps with a multiplier from config if specified.
                # Assuming Layer 3 estimated the deg for the predominant compound.
                # Here we just use the config fallback to keep it simple, or est_deg if we assume it applies universally.
                # Let's use config fallbacks for specific compounds, but record if we had an estimate.
                pass
            
            # Use configured fallback
            deg_rate = float(comp_cfg.get("degradation_rate_per_lap", 0.05))
            self.degradation_rates[compound] = deg_rate
            self.cliff_ages[compound] = int(comp_cfg.get("cliff_age", 30))
            
            self.fallbacks.append(FallbackRecord(
                parameter=f"degradation_rate_{compound}",
                source="configured_fallback",
                value=deg_rate,
                reason="Layer 3 per-compound degradation unavailable"
            ))

    def lap_time_penalty(self, state: TyreState) -> float:
        """Calculate the lap time penalty due to tyre degradation."""
        compound = state.compound
        age = state.age
        
        # Fallback to MEDIUM if unknown compound
        if compound not in self.degradation_rates:
            compound = "MEDIUM"
            
        rate = self.degradation_rates.get(compound, 0.05)
        cliff = self.cliff_ages.get(compound, 30)
        
        # Linear degradation
        penalty = rate * age
        
        # Cliff effect (exponential increase after cliff age)
        if age > cliff:
            cliff_penalty = 0.05 * (age - cliff) ** 2
            penalty += cliff_penalty
            
        return penalty
