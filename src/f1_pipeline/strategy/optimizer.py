"""Main strategy optimization orchestrator."""
from __future__ import annotations

import logging
from typing import Callable

from f1_pipeline.core.config import RuntimeConfig
from f1_pipeline.core.hashing import hash_dict
from f1_pipeline.core.paths import ProjectPaths, slugify_path_component
from f1_pipeline.db.repositories import StrategyAssetsRepository, StrategyRunsRepository
from f1_pipeline.ingestion.storage import StorageManager
from f1_pipeline.simulation.engine import SimulationEngine
from f1_pipeline.simulation.monte_carlo.runner import MonteCarloRunner
from f1_pipeline.simulation.scenario import Scenario
from f1_pipeline.strategy.algorithms import ExhaustiveOptimizer
from f1_pipeline.strategy.evaluator import StrategyEvaluator
from f1_pipeline.strategy.objectives import CompositeObjective, RaceTimeObjective, RobustnessObjective
from f1_pipeline.strategy.pareto import identify_pareto_frontier
from f1_pipeline.strategy.ranking import rank_strategies
from f1_pipeline.strategy.schemas import OptimizationResult, Strategy
from f1_pipeline.strategy.search_space import PitWindowSpace, SearchSpace, StopsSpace
from f1_pipeline.strategy.sensitivity import run_sensitivity_analysis

logger = logging.getLogger(__name__)


class StrategyOptimizationPipeline:
    def __init__(self, config: RuntimeConfig, paths: ProjectPaths):
        self.config = config
        self.paths = paths
        self.storage = StorageManager()
        
        self.runs_repo = StrategyRunsRepository()
        self.assets_repo = StrategyAssetsRepository()
        
    def execute(
        self,
        base_scenario: Scenario,
        layer3_params: dict,
        layer2_features: dict | None = None,
        algorithm: str = "exhaustive",
        objective: str = "race_time",
        monte_carlo: bool = False,
        seed: int = 42,
        force: bool = False,
        pareto: bool = False,
        sensitivity: bool = False,
        source_sim_run_id: str | None = None
    ) -> OptimizationResult:
        """Run the strategy optimization pipeline."""
        
        event_slug = slugify_path_component(base_scenario.event)
        session_slug = slugify_path_component(base_scenario.session_type)
        driver = base_scenario.driver_code.upper()
        
        # 1. Config hash and idempotency check
        strat_config = self.config.values.get("strategy", {})
        config_hash = hash_dict({
            "algorithm": algorithm,
            "objective": objective,
            "monte_carlo": monte_carlo,
            "seed": seed,
            "strategy_config": strat_config,
            "base_scenario_hash": base_scenario.scenario_hash()
        })
        
        # In a real app we'd query runs_repo to check if config_hash is already completed and reuse.
        # 2. Create Run Record
        run_id = self.runs_repo.create_started(
            algorithm=algorithm,
            objective=objective,
            config_hash=config_hash,
            source_simulation_context_id=source_sim_run_id
        )
        logger.info(f"Started Strategy Optimization Run: {run_id}")
        
        try:
            # 3. Construct Search Space
            space = self._build_search_space(base_scenario, strat_config)
            warnings = space.validate_space()
            if warnings:
                logger.warning(f"Search space validation warnings: {warnings}")
                
            # 4. Setup Evaluator
            evaluator = self._setup_evaluator(base_scenario, layer3_params, layer2_features, monte_carlo, seed)
            
            # 5. Setup Optimizer
            optimizer = self._get_optimizer(algorithm)
            
            # 6. Setup Objective
            objective_func = self._get_objective(objective, strat_config)
            
            # 7. Execute Optimization
            logger.info(f"Running optimizer '{algorithm}' with objective '{objective}'...")
            evaluations = optimizer.optimize(space, evaluator)
            
            # 8. Calculate Objective Scores
            for ev in evaluations:
                ev.objective_score = objective_func.score(ev)
                
            # 9. Rank Strategies
            ranked_df = rank_strategies(evaluations)
            
            # 10. Pareto Frontier (Optional)
            if pareto:
                # Typically minimize race_time, pit_stops, maybe risk
                metrics = ["race_time", "pit_stops"]
                if monte_carlo:
                    metrics.append("std_race_time")
                    
                ranked_df = identify_pareto_frontier(ranked_df, minimize_metrics=metrics)
                
            # 11. Select Best
            valid_df = ranked_df[ranked_df.get("is_valid", ranked_df["constraint_status"] == "valid")]
            best_strategy = None
            best_score = None
            best_time = None
            
            if not valid_df.empty:
                # The dataframe is already sorted by rank (so best valid is at index 0 of valid_df)
                best_row = valid_df.iloc[0]
                best_hash = best_row["strategy_hash"]
                best_score = best_row["objective_score"]
                best_time = best_row["race_time"]
                
                # Find the StrategyEvaluation object
                best_eval = next((e for e in evaluations if e.strategy_hash == best_hash), None)
                if best_eval:
                    best_strategy = best_eval.strategy
                    
            result = OptimizationResult(
                optimization_run_id=run_id,
                best_strategy=best_strategy,
                best_score=best_score,
                best_race_time=best_time,
                strategies_evaluated=len(evaluations),
                strategies_valid=len(valid_df),
                strategies_rejected=len(evaluations) - len(valid_df),
                algorithm=algorithm,
                objective=objective,
                pareto_frontier_size=ranked_df["is_pareto_optimal"].sum() if pareto else 0,
                status="success"
            )
            
            # 12. Save Results and Definitions
            out_dir = self.paths.processed / "strategies" / str(base_scenario.season) / event_slug / session_slug / driver / "optimization" / run_id
            out_dir.mkdir(parents=True, exist_ok=True)
            
            # Save definition and result for each evaluation
            for ev in evaluations:
                # Register definition
                self.assets_repo.create_strategy_definition(ev.strategy_hash, ev.strategy.model_dump(mode="json"))
                
            # Save Ranked Parquet
            ranked_path = out_dir / "ranked_strategies.parquet"
            ranked_df.to_parquet(ranked_path, index=False)
            self.assets_repo.create_asset(run_id, "ranked_strategies", str(ranked_path), config_hash, "parquet", len(ranked_df))
            
            if pareto:
                pareto_df = ranked_df[ranked_df["is_pareto_optimal"] == True]
                pareto_path = out_dir / "pareto_frontier.parquet"
                pareto_df.to_parquet(pareto_path, index=False)
                self.assets_repo.create_asset(run_id, "pareto_frontier", str(pareto_path), config_hash, "parquet", len(pareto_df))
                
            # 13. Sensitivity Analysis (Optional)
            if sensitivity and best_strategy:
                # E.g. Perturb deg and pit loss
                perturbations = {
                    "tyre_degradation": [-0.05, 0.05],
                    "pit_loss": [-2.0, 2.0]
                }
                sens_df = run_sensitivity_analysis(best_strategy, evaluator, objective_func, perturbations)
                sens_path = out_dir / "sensitivity.parquet"
                sens_df.to_parquet(sens_path, index=False)
                self.assets_repo.create_asset(run_id, "sensitivity", str(sens_path), config_hash, "parquet", len(sens_df))
                
            if best_strategy:
                self.storage.save_json(best_strategy.model_dump(mode="json"), out_dir / "best_strategy.json")
                
            self.runs_repo.mark_success(run_id)
            logger.info("Strategy Optimization completed successfully.")
            return result
            
        except Exception as e:
            logger.error(f"Strategy Optimization failed: {e}")
            self.runs_repo.mark_failed(run_id, str(e))
            raise
            
    def _build_search_space(self, base_scenario: Scenario, strat_config: dict) -> SearchSpace:
        compounds = strat_config.get("compounds", {}).get("available", ["SOFT", "MEDIUM", "HARD"])
        stops = strat_config.get("stops", {})
        min_stops = stops.get("minimum", 1)
        max_stops = stops.get("maximum", 3)
        min_stint = strat_config.get("stint", {}).get("minimum_laps", 5)
        
        return SearchSpace(
            driver_code=base_scenario.driver_code,
            total_laps=base_scenario.total_laps,
            compounds=compounds,
            stops=StopsSpace(min=min_stops, max=max_stops),
            stint_min_laps=min_stint,
            pit_windows=None # Example: Could be parsed from config if we wanted
        )
        
    def _setup_evaluator(
        self,
        base_scenario: Scenario,
        layer3_params: dict,
        layer2_features: dict | None,
        monte_carlo: bool,
        seed: int
    ) -> StrategyEvaluator:
        
        def engine_factory():
            return SimulationEngine(
                config=self.config.values,
                layer3_params=layer3_params,
                layer2_features=layer2_features or {}
            )
            
        def runner_factory():
            return MonteCarloRunner(self.config.values, layer3_params)
            
        return StrategyEvaluator(
            base_scenario=base_scenario,
            simulation_engine_factory=engine_factory,
            monte_carlo_runner_factory=runner_factory if monte_carlo else None,
            monte_carlo=monte_carlo,
            seed=seed,
            simulation_config=self.config.values.get("simulation", {})
        )
        
    def _get_optimizer(self, algorithm: str):
        if algorithm == "exhaustive":
            return ExhaustiveOptimizer()
        elif algorithm == "bayesian":
            from f1_pipeline.strategy.algorithms.bayesian import BayesianOptimizer
            return BayesianOptimizer()
        raise ValueError(f"Unknown optimization algorithm: {algorithm}")
        
    def _get_objective(self, objective: str, strat_config: dict):
        if objective == "race_time":
            return RaceTimeObjective()
        elif objective == "robustness":
            return RobustnessObjective()
        elif objective == "composite":
            weights = strat_config.get("objective", {})
            return CompositeObjective(weights)
        raise ValueError(f"Unknown objective: {objective}")
