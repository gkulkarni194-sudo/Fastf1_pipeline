"""Strategy evaluator linking Layer 5 to Layer 4."""
from __future__ import annotations

import logging
from typing import Any, Callable

from f1_pipeline.simulation.engine import SimulationEngine
from f1_pipeline.simulation.scenario import Scenario
from f1_pipeline.simulation.scenario import PitStopSpec as L4PitStopSpec
from f1_pipeline.simulation.scenario import TyreStintSpec as L4TyreStintSpec
from f1_pipeline.strategy.constraints import evaluate_dynamic_constraints, evaluate_static_constraints
from f1_pipeline.strategy.schemas import Strategy, StrategyEvaluation
from f1_pipeline.strategy.search_space import SearchSpace
from f1_pipeline.strategy.strategy_hash import hash_strategy

logger = logging.getLogger(__name__)


class StrategyEvaluator:
    """Evaluates a Strategy by converting it to a Scenario and running Layer 4."""
    
    def __init__(
        self,
        base_scenario: Scenario,
        simulation_engine_factory: Callable[[], SimulationEngine],
        monte_carlo_runner_factory: Callable[[], Any] | None = None,
        monte_carlo: bool = False,
        seed: int = 42,
        simulation_config: dict | None = None,
    ):
        self.base_scenario = base_scenario
        self.simulation_engine_factory = simulation_engine_factory
        self.monte_carlo_runner_factory = monte_carlo_runner_factory
        self.monte_carlo = monte_carlo
        self.seed = seed
        self.simulation_config = simulation_config or {}
        
        # Simple in-memory cache to prevent identical Layer 4 runs within one optimization execution
        self._cache: dict[str, StrategyEvaluation] = {}
        
    def evaluate(self, strategy: Strategy, space: SearchSpace) -> StrategyEvaluation:
        """Run the strategy through constraints and Layer 4 simulation."""
        
        # 1. Hash the strategy
        shash = hash_strategy(strategy)
        
        # 2. Check cache
        if shash in self._cache:
            return self._cache[shash]
            
        # 3. Static constraints
        static_res = evaluate_static_constraints(strategy, space)
        if not static_res.valid:
            evaluation = StrategyEvaluation(
                strategy_hash=shash,
                strategy=strategy,
                constraint_status=f"invalid_static: {', '.join(static_res.violations)}"
            )
            self._cache[shash] = evaluation
            return evaluation
            
        # 4. Convert Strategy -> Layer 4 Scenario
        scenario = self._create_layer4_scenario(strategy)
        
        # 5. Run Layer 4 Simulation
        if self.monte_carlo and self.monte_carlo_runner_factory:
            mc_runner = self.monte_carlo_runner_factory()
            
            def run_iter(params, iter_seed):
                # We need a new engine instance per thread if we parallelize
                # Currently we rely on the factory handling it or engine being safe
                iter_engine = self.simulation_engine_factory()
                # Overwrite params (for Layer 3 perturbations)
                iter_engine.layer3_params = params
                return iter_engine.run_deterministic(scenario, iter_seed)
                
            mc_result = mc_runner.run(self.seed, run_iter)
            
            # Extract metrics
            if mc_result.success:
                evaluation = StrategyEvaluation(
                    strategy_hash=shash,
                    strategy=strategy,
                    constraint_status="valid",
                    race_time=mc_result.summary.mean_race_time,
                    mean_race_time=mc_result.summary.mean_race_time,
                    std_race_time=mc_result.summary.std_race_time,
                    p05_race_time=mc_result.summary.p05_race_time,
                    p50_race_time=mc_result.summary.p50_race_time,
                    p95_race_time=mc_result.summary.p95_race_time,
                )
            else:
                evaluation = StrategyEvaluation(
                    strategy_hash=shash,
                    strategy=strategy,
                    constraint_status=f"invalid_mc_simulation: {mc_result.error_message}"
                )
                
        else:
            engine = self.simulation_engine_factory()
            result = engine.run_deterministic(scenario, self.seed)
            
            # Dynamic constraints
            dyn_res = evaluate_dynamic_constraints(result, self.simulation_config)
            if not dyn_res.valid:
                evaluation = StrategyEvaluation(
                    strategy_hash=shash,
                    strategy=strategy,
                    constraint_status=f"invalid_dynamic: {', '.join(dyn_res.violations)}"
                )
            else:
                rt = result.race_result.total_race_time if result.race_result else None
                evaluation = StrategyEvaluation(
                    strategy_hash=shash,
                    strategy=strategy,
                    constraint_status="valid",
                    race_time=rt,
                    simulated_laps=result.race_result.total_laps if result.race_result else None
                )
                
        self._cache[shash] = evaluation
        return evaluation
        
    def _create_layer4_scenario(self, strategy: Strategy) -> Scenario:
        """Adapter from Layer 5 Strategy to Layer 4 Scenario."""
        # We start with the base scenario configuration (event, season, weather, fuel, laps)
        l4_scenario = self.base_scenario.model_copy(deep=True)
        
        # Override the strategy parts
        l4_scenario.driver_code = strategy.driver_code
        
        l4_tyres = [
            L4TyreStintSpec(compound=s.compound, start_lap=s.start_lap, end_lap=s.end_lap)
            for s in strategy.stints
        ]
        
        l4_pits = [
            L4PitStopSpec(lap=p.lap, pit_loss_seconds=p.pit_loss_seconds, change_compound_to=p.change_compound_to)
            for p in strategy.pit_stops
        ]
        
        l4_scenario.tyre_strategy = l4_tyres
        l4_scenario.pit_stops = l4_pits
        
        # Re-validate at Layer 4 boundary just to be safe
        warnings = l4_scenario.validate_scenario()
        if warnings:
            logger.warning(f"Layer 4 scenario validation produced warnings: {warnings}")
            
        return l4_scenario
