"""Composite objective."""
from __future__ import annotations

from f1_pipeline.strategy.schemas import StrategyEvaluation

from .race_time import RaceTimeObjective
from .robustness import RobustnessObjective


class CompositeObjective:
    """Objective: weighted combination of other objectives."""
    
    def __init__(self, weights: dict[str, float]):
        """Initialize with weights.
        
        Example:
            {"race_time": 1.0, "risk": 0.5}
        """
        self.weights = weights
        self.race_time_obj = RaceTimeObjective()
        self.robustness_obj = RobustnessObjective()
        
    def score(self, evaluation: StrategyEvaluation) -> float | None:
        if evaluation.constraint_status != "valid":
            return None
            
        total_score = 0.0
        
        if "race_time" in self.weights and self.weights["race_time"] > 0:
            rt_score = self.race_time_obj.score(evaluation)
            if rt_score is not None:
                total_score += self.weights["race_time"] * rt_score
                
        if "risk" in self.weights and self.weights["risk"] > 0:
            risk_score = self.robustness_obj.score(evaluation)
            if risk_score is not None:
                # Risk score might be an order of magnitude smaller than race time.
                # In a real system, you'd normalize these or rely on user weights to balance them.
                total_score += self.weights["risk"] * risk_score
                
        return total_score
