"""Exhaustive search strategy optimizer."""
from __future__ import annotations

import logging

from f1_pipeline.strategy.algorithms.base import StrategyOptimizer
from f1_pipeline.strategy.evaluator import StrategyEvaluator
from f1_pipeline.strategy.generators.race_strategies import RaceStrategyGenerator
from f1_pipeline.strategy.schemas import StrategyEvaluation
from f1_pipeline.strategy.search_space import SearchSpace

logger = logging.getLogger(__name__)


class ExhaustiveOptimizer(StrategyOptimizer):
    """Evaluates all valid candidates in the search space."""
    
    def optimize(self, space: SearchSpace, evaluator: StrategyEvaluator) -> list[StrategyEvaluation]:
        generator = RaceStrategyGenerator(space)
        evaluations = []
        
        count = 0
        logger.info("Generating and evaluating exhaustive search space...")
        
        for candidate in generator.generate():
            eval_result = evaluator.evaluate(candidate, space)
            evaluations.append(eval_result)
            count += 1
            
            if count % 100 == 0:
                logger.info(f"Evaluated {count} strategies...")
                
        logger.info(f"Exhaustive optimization completed. Total evaluated: {count}")
        return evaluations
