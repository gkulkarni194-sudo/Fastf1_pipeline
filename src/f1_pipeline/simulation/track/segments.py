"""Track segments (not heavily used in empirical model)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class TrackSegment:
    """Represents a segment of track for more detailed models.
    
    Not primarily used by EmpiricalTrackModel, but defined for future
    geometry-based simulation extensions.
    """
    id: int
    segment_type: Literal["straight", "corner"]
    length_m: float
    radius_m: float | None = None
    drs_zone: bool = False
