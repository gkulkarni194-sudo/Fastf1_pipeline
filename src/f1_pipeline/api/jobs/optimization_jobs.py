"""Optimization Job wrapper."""
from __future__ import annotations

import logging

from f1_pipeline.core.config import RuntimeConfig
from f1_pipeline.core.paths import ProjectPaths
from f1_pipeline.simulation.scenario import Scenario
from f1_pipeline.strategy.optimizer import StrategyOptimizationPipeline

logger = logging.getLogger(__name__)


def execute_optimization_job(
    config: RuntimeConfig,
    paths: ProjectPaths,
    base_scenario_dict: dict,
    layer3_params: dict,
    algorithm: str,
    objective: str,
    monte_carlo: bool,
    seed: int,
    pareto: bool,
    sensitivity: bool
) -> str:
    """Wrapper function to execute Layer 5 optimization in a thread.
    
    Returns the optimization run ID on success.
    """
    logger.info("Initializing Optimization Pipeline in background worker...")
    
    base_scenario = Scenario(**base_scenario_dict)
    
    pipeline = StrategyOptimizationPipeline(config, paths)
    
    result = pipeline.execute(
        base_scenario=base_scenario,
        layer3_params=layer3_params,
        layer2_features={},
        algorithm=algorithm,
        objective=objective,
        monte_carlo=monte_carlo,
        seed=seed,
        force=False,
        pareto=pareto,
        sensitivity=sensitivity
    )
    
    if result.status != "success":
        raise RuntimeError(f"Optimization failed. Checked {result.strategies_evaluated} candidates.")
        
    return result.optimization_run_id
