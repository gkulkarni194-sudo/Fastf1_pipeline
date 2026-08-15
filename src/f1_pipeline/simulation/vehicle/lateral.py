"""Lateral vehicle dynamics."""
from __future__ import annotations

from f1_pipeline.simulation.vehicle.dynamics import VehicleDynamicsModel


class LateralModel:
    """Models cornering capacity."""

    def __init__(self, dynamics: VehicleDynamicsModel):
        self.dyn = dynamics
        
    def downforce(self, speed_ms: float) -> float:
        """F_down = 0.5 * rho * ClA * v^2"""
        return 0.5 * self.dyn.rho * self.dyn.cla * (speed_ms ** 2)
        
    def max_cornering_speed(self, radius_m: float, mass_kg: float, tyre_grip_mult: float, track_grip_mult: float) -> float:
        """Calculate maximum speed through a corner of given radius.
        
        F_lat = m * v^2 / R
        F_lat_max = mu * (m * g + F_down)
        m * v^2 / R = mu * m * g + mu * 0.5 * rho * ClA * v^2
        v^2 * (m/R - mu * 0.5 * rho * ClA) = mu * m * g
        v = sqrt((mu * m * g) / (m/R - mu * 0.5 * rho * ClA))
        """
        # Base grip from layer 3 * tyre state * track state
        mu = self.dyn.grip_multiplier * tyre_grip_mult * track_grip_mult
        
        numerator = mu * mass_kg * self.dyn.g
        denominator = (mass_kg / radius_m) - (mu * 0.5 * self.dyn.rho * self.dyn.cla)
        
        if denominator <= 0:
            # Downforce exceeds mass/radius requirements -> theoretically infinite cornering speed (flat out)
            return float('inf')
            
        return (numerator / denominator) ** 0.5
