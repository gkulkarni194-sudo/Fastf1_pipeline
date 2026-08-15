"""Vehicle dynamics models."""
from __future__ import annotations

from typing import Any

from f1_pipeline.simulation.schemas import FallbackRecord


class VehicleDynamicsModel:
    """Core vehicle dynamics model integrating longitudinal and lateral forces."""

    def __init__(self, config: dict[str, Any], layer3_params: dict[str, Any]):
        self.config = config
        self.layer3_params = layer3_params
        self.fallbacks: list[FallbackRecord] = []
        
        # Load core parameters, falling back where necessary
        self.cda = self._load_param("effective_drag_parameter", 1.5)
        self.cla = self._load_param("effective_downforce_parameter", 4.0)
        self.drive_force = self._load_param("effective_drive_force", 8000.0)
        self.grip_multiplier = self._load_param("effective_grip_parameter", 2.0)
        
        # Constants
        constants = config.get("constants", {})
        self.rho = float(constants.get("air_density", {}).get("value", 1.225))
        self.g = float(constants.get("gravity", {}).get("value", 9.80665))
        self.crr = float(constants.get("rolling_resistance_reference", {}).get("value", 0.012))
        
    def _load_param(self, name: str, fallback_value: float) -> float:
        val = self.layer3_params.get(name)
        if val is not None:
            return float(val)
        
        self.fallbacks.append(FallbackRecord(
            parameter=name,
            source="configured_fallback",
            value=fallback_value,
            reason="Layer 3 estimate unavailable"
        ))
        return fallback_value
