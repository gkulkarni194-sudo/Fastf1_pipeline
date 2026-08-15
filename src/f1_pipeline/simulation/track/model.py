"""Track representation."""
from __future__ import annotations

from typing import Any

from f1_pipeline.simulation.schemas import FallbackRecord


class EmpiricalTrackModel:
    """An empirical track model based on base lap time.
    
    This avoids needing full synthetic 3D geometry. Lap times are computed
    by taking a baseline lap time and applying dynamic effects (tyre grip,
    tyre degradation, fuel mass, weather, track evolution).
    """

    def __init__(self, config: dict[str, Any], layer2_features: dict[str, Any] | None = None):
        self.config = config.get("track", {})
        self.layer2_features = layer2_features or {}
        self.fallbacks: list[FallbackRecord] = []
        
        # Load base lap time (median lap time from L2 if available, else config)
        median_lap_time = self.layer2_features.get("median_lap_time_seconds")
        
        if median_lap_time is not None:
            self.base_lap_time = float(median_lap_time)
            self.source = "layer2_features"
        else:
            self.base_lap_time = float(self.config.get("base_lap_time_seconds", 90.0))
            self.source = "configured_fallback"
            self.fallbacks.append(FallbackRecord(
                parameter="base_lap_time",
                source="configured_fallback",
                value=self.base_lap_time,
                reason="Layer 2 median lap time unavailable"
            ))
            
        self.total_distance_m = float(self.config.get("total_distance_m", 5000.0))
