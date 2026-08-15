"""Sensitivity analysis for the optimal strategy."""
from __future__ import annotations

import logging

import pandas as pd

from f1_pipeline.strategy.evaluator import StrategyEvaluator
from f1_pipeline.strategy.objectives.race_time import StrategyObjective
from f1_pipeline.strategy.schemas import Strategy

logger = logging.getLogger(__name__)


def run_sensitivity_analysis(
    strategy: Strategy,
    evaluator: StrategyEvaluator,
    objective: StrategyObjective,
    perturbations: dict[str, list[float]]
) -> pd.DataFrame:
    """Run sensitivity analysis on a single strategy by perturbing parameters.
    
    This is an analysis feature, executed after optimization, to see how the best
    strategy performs if underlying simulation parameters change slightly.
    """
    logger.info("Running sensitivity analysis...")
    
    # We must operate directly on the evaluator's simulation engine configs/params.
    # We create a new evaluator for each perturbation to avoid corrupting state.
    # Note: the SearchSpace doesn't matter for evaluation since it's already a generated strategy.
    # We will pass a dummy search space.
    from f1_pipeline.strategy.search_space import SearchSpace, StopsSpace
    dummy_space = SearchSpace(
        driver_code=strategy.driver_code,
        total_laps=1,
        compounds=[],
        stops=StopsSpace(min=0, max=10),
        stint_min_laps=1
    )
    
    records = []
    
    # Baseline
    eval_base = evaluator.evaluate(strategy, dummy_space)
    eval_base.objective_score = objective.score(eval_base)
    records.append({
        "parameter": "baseline",
        "perturbation": 0.0,
        "race_time": eval_base.race_time,
        "objective_score": eval_base.objective_score,
        "constraint_status": eval_base.constraint_status
    })
    
    # Run perturbations
    for param, values in perturbations.items():
        for val in values:
            if val == 0.0:
                continue
                
            # Create a perturbed evaluator (shallow copy of configs, deep copy of perturbed parts)
            perturbed_evaluator = _create_perturbed_evaluator(evaluator, param, val)
            
            # Evaluate
            eval_p = perturbed_evaluator.evaluate(strategy, dummy_space)
            eval_p.objective_score = objective.score(eval_p)
            
            records.append({
                "parameter": param,
                "perturbation": val,
                "race_time": eval_p.race_time,
                "objective_score": eval_p.objective_score,
                "constraint_status": eval_p.constraint_status
            })
            
    return pd.DataFrame(records)


def _create_perturbed_evaluator(base_evaluator: StrategyEvaluator, param: str, val: float) -> StrategyEvaluator:
    """Helper to create a new evaluator with slightly modified configs."""
    # This is a bit of a hack to demonstrate sensitivity.
    # In a full production system, we'd have a more robust parameter override system.
    import copy
    
    new_sim_config = copy.deepcopy(base_evaluator.simulation_config)
    
    if param == "pit_loss":
        # val is in seconds (e.g., +2s)
        current = new_sim_config.get("pit_stop", {}).get("default_loss_seconds", 22.0)
        if "pit_stop" not in new_sim_config:
            new_sim_config["pit_stop"] = {}
        new_sim_config["pit_stop"]["default_loss_seconds"] = current + val
        
    elif param == "tyre_degradation":
        # val is a multiplier (e.g., +0.05 for +5%)
        # Apply to all compounds
        if "tyres" in new_sim_config and "compounds" in new_sim_config["tyres"]:
            for comp, comp_data in new_sim_config["tyres"]["compounds"].items():
                comp_data["degradation_rate_per_lap"] *= (1.0 + val)
                
    elif param == "fuel_consumption":
        if "fuel" in new_sim_config:
            new_sim_config["fuel"]["consumption_per_lap_kg"] *= (1.0 + val)
            
    def new_engine_factory():
        # Instantiate a new engine using the original factory to get the base params
        engine = base_evaluator.simulation_engine_factory()
        # Overwrite its config
        engine.config = new_sim_config
        return engine
        
    return StrategyEvaluator(
        base_scenario=base_evaluator.base_scenario,
        simulation_engine_factory=new_engine_factory,
        monte_carlo_runner_factory=base_evaluator.monte_carlo_runner_factory,
        monte_carlo=base_evaluator.monte_carlo,
        seed=base_evaluator.seed,
        simulation_config=new_sim_config
    )
