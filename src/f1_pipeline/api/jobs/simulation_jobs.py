"""Simulation Job wrapper."""
from __future__ import annotations

import logging

from f1_pipeline.core.config import RuntimeConfig
from f1_pipeline.core.paths import ProjectPaths
from f1_pipeline.simulation.pipeline import Layer4SimulationPipeline
from f1_pipeline.simulation.scenario import Scenario

logger = logging.getLogger(__name__)


def execute_simulation_job(
    config: RuntimeConfig,
    paths: ProjectPaths,
    scenario_dict: dict,
    layer3_params: dict,
    seed: int,
    monte_carlo: bool
) -> str:
    """Wrapper function to execute Layer 4 simulation in a thread.
    
    Returns the simulation run ID on success.
    """
    logger.info("Initializing Simulation Pipeline in background worker...")
    
    # Reconstruct scenario
    scenario = Scenario(**scenario_dict)
    
    pipeline = Layer4SimulationPipeline(config, paths)
    
    result = pipeline.execute(
        scenario=scenario,
        layer3_params=layer3_params,
        layer2_features={},
        monte_carlo=monte_carlo,
        seed=seed
    )
    
    if not result.success:
        raise RuntimeError(f"Simulation failed: {result.message}")
        
    return result.simulation_run_id
