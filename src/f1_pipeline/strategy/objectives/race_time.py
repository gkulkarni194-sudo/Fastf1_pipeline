"""Race time objective."""
from __future__ import annotations

from typing import Protocol

from f1_pipeline.strategy.schemas import StrategyEvaluation


class StrategyObjective(Protocol):
    def score(self, evaluation: StrategyEvaluation) -> float | None:
        """Calculate the objective score. Lower is better."""
        ...


class RaceTimeObjective:
    """Primary objective: minimize total simulated race time."""
    
    def score(self, evaluation: StrategyEvaluation) -> float | None:
        if evaluation.constraint_status != "valid":
            return None
            
        if evaluation.race_time is not None:
            return evaluation.race_time
            
        if evaluation.mean_race_time is not None:
            return evaluation.mean_race_time
            
        return None
