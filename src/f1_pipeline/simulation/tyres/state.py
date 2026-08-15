"""Tyre state representation."""
from __future__ import annotations

from dataclasses import dataclass

@dataclass
class TyreState:
    """Represents the state of the tyres on the vehicle."""
    compound: str
    age: int
    grip_multiplier: float
    
    def copy(self) -> TyreState:
        return TyreState(
            compound=self.compound,
            age=self.age,
            grip_multiplier=self.grip_multiplier,
        )
