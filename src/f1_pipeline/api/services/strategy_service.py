"""Strategy optimization service."""
from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from f1_pipeline.api.jobs.manager import JobManager
from f1_pipeline.api.jobs.optimization_jobs import execute_optimization_job
from f1_pipeline.api.schemas.optimizations import OptimizationCreateRequest
from f1_pipeline.api.schemas.simulations import JobQueuedResponse
from f1_pipeline.core.config import RuntimeConfig
from f1_pipeline.core.paths import ProjectPaths, slugify_path_component
from f1_pipeline.db.repositories.strategy_runs import StrategyRunsRepository


class StrategyService:
    def __init__(self, config: RuntimeConfig, paths: ProjectPaths, job_manager: JobManager):
        self.config = config
        self.paths = paths
        self.job_manager = job_manager
        self.repo = StrategyRunsRepository()
        
    def _fetch_layer3_params(self, season: int, event: str, session: str, driver: str) -> dict:
        # Same as simulation service
        slug_ev = slugify_path_component(event)
        slug_ses = slugify_path_component(session)
        physics_dir = self.paths.processed / "physics" / str(season) / slug_ev / "q" / driver.upper()
            
        if not physics_dir.exists():
            raise HTTPException(status_code=404, detail="Required Layer 3 physics data not found.")
            
        params = {}
        for fname in ["aero_parameters.json", "cornering_parameters.json", "longitudinal_parameters.json", "tyre_parameters.json"]:
            p = physics_dir / fname
            if p.exists():
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if isinstance(v, dict) and "value" in v:
                            params[k] = v["value"]
                        else:
                            params[k] = v
        return params
        
    def create_optimization(self, request: OptimizationCreateRequest) -> JobQueuedResponse:
        """Submit a new strategy optimization to the background job manager."""
        
        # 1. Fetch layer 3 dependencies
        l3_params = self._fetch_layer3_params(request.season, request.event, request.session, request.driver)
        
        # 2. Build a base scenario from the request
        base_scenario_dict = {
            "season": request.season,
            "event": request.event,
            "session_type": request.session,
            "driver_code": request.driver,
            "total_laps": 57, # Usually fetched from event metadata
            "starting_fuel_kg": 110.0,
            "tyre_strategy": [],
            "pit_stops": []
        }
        
        # 3. Submit job
        job_id = self.job_manager.submit(
            job_type="optimization",
            payload={"season": request.season, "event": request.event, "driver": request.driver},
            func=execute_optimization_job,
            config=self.config,
            paths=self.paths,
            base_scenario_dict=base_scenario_dict,
            layer3_params=l3_params,
            algorithm=request.algorithm,
            objective=request.objective,
            monte_carlo=request.monte_carlo,
            seed=request.seed,
            pareto=True,
            sensitivity=True
        )
        
        return JobQueuedResponse(job_id=job_id, status="queued", message="Optimization job queued successfully.")
