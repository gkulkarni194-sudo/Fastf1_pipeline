"""Longitudinal vehicle dynamics."""
from __future__ import annotations

from f1_pipeline.simulation.vehicle.dynamics import VehicleDynamicsModel


class LongitudinalModel:
    """Models straight-line acceleration and braking."""

    def __init__(self, dynamics: VehicleDynamicsModel):
        self.dyn = dynamics
        
    def drag_force(self, speed_ms: float) -> float:
        """F_drag = 0.5 * rho * CdA * v^2"""
        return 0.5 * self.dyn.rho * self.dyn.cda * (speed_ms ** 2)
        
    def rolling_resistance(self, mass_kg: float) -> float:
        """F_rr = Crr * m * g"""
        return self.dyn.crr * mass_kg * self.dyn.g
        
    def acceleration(self, speed_ms: float, mass_kg: float, throttle_fraction: float = 1.0) -> float:
        """Calculate longitudinal acceleration.
        
        a = (F_drive * throttle - F_drag - F_rr) / m
        """
        f_drive = self.dyn.drive_force * throttle_fraction
        f_drag = self.drag_force(speed_ms)
        f_rr = self.rolling_resistance(mass_kg)
        
        f_net = f_drive - f_drag - f_rr
        return f_net / mass_kg
        
    def max_speed(self, mass_kg: float) -> float:
        """Calculate terminal velocity where F_drive = F_drag + F_rr.
        
        v_max = sqrt((F_drive - F_rr) / (0.5 * rho * CdA))
        """
        f_rr = self.rolling_resistance(mass_kg)
        f_net_aero = self.dyn.drive_force - f_rr
        
        if f_net_aero <= 0:
            return 0.0
            
        return (f_net_aero / (0.5 * self.dyn.rho * self.dyn.cda)) ** 0.5
