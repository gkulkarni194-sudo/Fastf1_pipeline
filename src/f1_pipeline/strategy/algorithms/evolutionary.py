"""Evolutionary optimization stub."""
from __future__ import annotations

from f1_pipeline.strategy.algorithms.base import StrategyOptimizer
from f1_pipeline.strategy.evaluator import StrategyEvaluator
from f1_pipeline.strategy.schemas import StrategyEvaluation
from f1_pipeline.strategy.search_space import SearchSpace


class EvolutionaryOptimizer(StrategyOptimizer):
    """Stub for Evolutionary Algorithm."""
    
    def optimize(self, space: SearchSpace, evaluator: StrategyEvaluator) -> list[StrategyEvaluation]:
        raise NotImplementedError("Evolutionary optimization is not yet implemented. Use exhaustive algorithm.")
