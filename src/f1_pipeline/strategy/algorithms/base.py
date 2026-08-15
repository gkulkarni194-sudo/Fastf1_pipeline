"""Base strategy optimizer interface."""
from __future__ import annotations

from typing import Protocol

from f1_pipeline.strategy.evaluator import StrategyEvaluator
from f1_pipeline.strategy.schemas import StrategyEvaluation
from f1_pipeline.strategy.search_space import SearchSpace


class StrategyOptimizer(Protocol):
    """Protocol for strategy optimization algorithms."""
    
    def optimize(self, space: SearchSpace, evaluator: StrategyEvaluator) -> list[StrategyEvaluation]:
        """Run optimization and return evaluated strategies.
        
        The optimizer is responsible for:
        1. Generating candidate strategies based on the space.
        2. Passing them to the evaluator.
        3. Using evaluation results to guide further generation (if applicable).
        
        Returns:
            A list of all evaluated strategies. The orchestrator will handle ranking.
        """
        ...
