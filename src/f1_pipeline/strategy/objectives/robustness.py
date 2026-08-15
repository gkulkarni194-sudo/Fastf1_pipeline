"""Robustness objective."""
from __future__ import annotations

from f1_pipeline.strategy.schemas import StrategyEvaluation


class RobustnessObjective:
    """Objective: minimize risk/variance under uncertainty.
    
    This heavily penalizes strategies with a high p95 or large standard deviation.
    Requires Monte Carlo evaluations.
    """
    
    def score(self, evaluation: StrategyEvaluation) -> float | None:
        if evaluation.constraint_status != "valid":
            return None
            
        if evaluation.p95_race_time is not None and evaluation.mean_race_time is not None:
            # Simple risk metric: how much slower is the 95th percentile than the mean?
            # E.g., if mean is 5000s and p95 is 5050s, score is 50.
            # Lower score means less downside risk.
            return evaluation.p95_race_time - evaluation.mean_race_time
            
        if evaluation.std_race_time is not None:
            return evaluation.std_race_time
            
        return None
