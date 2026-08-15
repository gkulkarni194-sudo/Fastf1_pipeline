"""High-level Simulation Pipeline orchestrator."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from f1_pipeline.core.config import RuntimeConfig
from f1_pipeline.core.paths import ProjectPaths, slugify_path_component
from f1_pipeline.db.repositories import (
    PhysicsRunsRepository,
    SimulationAssetsRepository,
    SimulationRunsRepository,
)
from f1_pipeline.ingestion.storage import StorageManager
from f1_pipeline.simulation.engine import SimulationEngine
from f1_pipeline.simulation.monte_carlo.runner import MonteCarloRunner
from f1_pipeline.simulation.scenario import Scenario
from f1_pipeline.simulation.schemas import SimulationResult

logger = logging.getLogger(__name__)


class Layer4SimulationPipeline:
    def __init__(self, config: RuntimeConfig, paths: ProjectPaths):
        self.config = config
        self.paths = paths
        self.storage = StorageManager()
        self.physics_repo = PhysicsRunsRepository()
        self.sim_runs_repo = SimulationRunsRepository()
        self.sim_assets_repo = SimulationAssetsRepository()
        
    def execute(self, scenario: Scenario, run_monte_carlo: bool = False, seed: int = 42, force: bool = False) -> SimulationResult:
        """Execute the full simulation pipeline for a given scenario."""
        logger.info(f"Starting Layer 4 Simulation for {scenario.season} {scenario.event} {scenario.session_type} {scenario.driver_code}")
        
        # 1. Fetch Layer 3 Physics Parameters
        # For a real integration, we'd query PhysicsRunsRepository for the latest successful run
        # and load its parameters. For now, we simulate fetching them from the filesystem.
        event_slug = slugify_path_component(scenario.event)
        session_slug = slugify_path_component(scenario.session_type)
        driver_code = scenario.driver_code.upper()
        
        physics_dir = self.paths.processed / "physics" / str(scenario.season) / event_slug / session_slug / driver_code
        if not physics_dir.exists():
            raise FileNotFoundError(f"Layer 3 physics parameters not found at {physics_dir}. Run Layer 3 first.")
            
        layer3_params = {}
        for param_file in ["aero_parameters.json", "cornering_parameters.json", "longitudinal_parameters.json", "tyre_parameters.json"]:
            file_path = physics_dir / param_file
            if file_path.exists():
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Support extracting from a dict of parameter objects
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, dict) and "value" in v:
                                layer3_params[k] = v["value"]
                            else:
                                layer3_params[k] = v
            
        # 2. Fetch Layer 2 Features (optional, for empirical track model)
        layer2_features = {}
        features_path = self.paths.processed / "features" / str(scenario.season) / event_slug / session_slug / "session_features.json"
        if features_path.exists():
            with features_path.open("r", encoding="utf-8") as f:
                layer2_features = json.load(f)
                
        # 3. Hash Scenario & Register (Upsert)
        scenario_hash = scenario.scenario_hash()
        scenario_id = f"local-scen-{scenario_hash}"
        run_id = f"local-run-{scenario_hash}"
        
        try:
            existing_scenario_id = self.sim_assets_repo.find_scenario_by_hash(scenario_hash)
            
            if existing_scenario_id:
                scenario_id = existing_scenario_id
                logger.info(f"Found existing scenario with hash {scenario_hash}")
            else:
                scenario_id = self.sim_assets_repo.create_scenario(scenario_hash, scenario.model_dump(mode="json"))
                logger.info(f"Created new scenario with hash {scenario_hash}")
                
            # 4. Create Run Record
            run_id = self.sim_runs_repo.create_started(
                season=scenario.season,
                event=event_slug,
                session=session_slug,
                driver=driver_code,
                scenario_hash=scenario_hash
            )
            logger.info(f"Created simulation run record {run_id}")
        except Exception as e:
            logger.warning(f"Database unavailable for tracking run/scenario: {e}")
        
        try:
            # 5. Initialize Engine
            engine = SimulationEngine(
                config=self.config.values,
                layer3_params=layer3_params,
                layer2_features=layer2_features
            )
            
            # 6. Run Simulation
            if run_monte_carlo:
                logger.info(f"Running Monte Carlo simulation with seed {seed}...")
                mc_runner = MonteCarloRunner(self.config.values, layer3_params)
                
                # The runner needs a function that takes (params, seed) and returns a SimulationResult
                def run_iter(params, iter_seed):
                    iter_engine = SimulationEngine(self.config.values, params, layer2_features)
                    return iter_engine.run_deterministic(scenario, iter_seed)
                    
                mc_result = mc_runner.run(seed, run_iter)
                
                result = SimulationResult(
                    success=True,
                    mode="monte_carlo",
                    monte_carlo_result=mc_result,
                    fallbacks=engine.fallbacks # Using base fallbacks
                )
            else:
                logger.info(f"Running deterministic simulation...")
                result = engine.run_deterministic(scenario, seed)
                
            result.simulation_run_id = run_id
            result.scenario_id = scenario_id
            result.scenario_hash = scenario_hash
            
            if not result.success:
                raise RuntimeError(f"Simulation failed: {result.message}")
                
            # 7. Save Outputs
            out_dir = self.paths.processed / "simulations" / str(scenario.season) / event_slug / session_slug / driver_code
            out_dir.mkdir(parents=True, exist_ok=True)
            
            # Save main result payload (excluding large raw data)
            result_json_path = out_dir / "simulation_result.json"
            
            # To avoid huge JSON, we dump the result. For Monte Carlo, iterations could be large,
            # but we'll serialize everything together for now per the spec.
            asset = self.storage.save_json(result.model_dump(mode="json"), result_json_path)
            
            # 8. Register Asset
            try:
                self.sim_assets_repo.create_asset(
                    run_id=run_id,
                    asset_type="simulation_result",
                    file_path=asset.path,
                    checksum=asset.checksum,
                    file_format=asset.file_format,
                    row_count=asset.row_count
                )
            except Exception as e:
                logger.warning(f"Database unavailable to register asset: {e}")
            
            # 9. Mark Success
            summary = {
                "mode": result.mode,
                "scenario_hash": scenario_hash,
            }
            if result.mode == "deterministic" and result.race_result:
                summary["total_race_time"] = result.race_result.total_race_time
                summary["warnings_count"] = len(result.race_result.warnings)
            elif result.mode == "monte_carlo" and result.monte_carlo_result:
                summary["mean_race_time"] = result.monte_carlo_result.summary.mean_race_time
                
            try:
                self.sim_runs_repo.mark_success(run_id, summary)
            except Exception as e:
                logger.warning(f"Database unavailable to mark success: {e}")
                
            logger.info("Simulation pipeline completed successfully.")
            
            return result
            
        except Exception as e:
            logger.error(f"Simulation pipeline failed: {e}")
            try:
                self.sim_runs_repo.mark_failed(run_id, str(e))
            except Exception:
                pass
            raise
