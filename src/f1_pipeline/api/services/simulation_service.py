"""Simulation service."""
from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from f1_pipeline.api.jobs.manager import JobManager
from f1_pipeline.api.jobs.simulation_jobs import execute_simulation_job
from f1_pipeline.api.schemas.simulations import JobQueuedResponse, SimulationCreateRequest, SimulationResultResponse
from f1_pipeline.core.config import RuntimeConfig
from f1_pipeline.core.paths import ProjectPaths, slugify_path_component
from f1_pipeline.db.repositories.simulation_runs import SimulationRunsRepository


class SimulationService:
    def __init__(self, config: RuntimeConfig, paths: ProjectPaths, job_manager: JobManager):
        self.config = config
        self.paths = paths
        self.job_manager = job_manager
        self.repo = SimulationRunsRepository()
        
    def _fetch_layer3_params(self, season: int, event: str, session: str, driver: str) -> dict:
        slug_ev = slugify_path_component(event)
        slug_ses = slugify_path_component(session)
        physics_dir = self.paths.processed / "physics" / str(season) / slug_ev / slug_ses / driver.upper()
        
        if not physics_dir.exists() and slug_ses.lower() == "r":
            physics_dir = self.paths.processed / "physics" / str(season) / slug_ev / "q" / driver.upper()
            
        if not physics_dir.exists():
            raise HTTPException(status_code=404, detail="Required Layer 3 physics data not found for scenario.")
            
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
        
    def create_simulation(self, request: SimulationCreateRequest) -> JobQueuedResponse:
        """Submit a new simulation to the background job manager."""
        
        # 1. Fetch layer 3 dependencies
        l3_params = self._fetch_layer3_params(request.season, request.event, request.session, request.driver)
        
        # 2. Serialize Scenario
        scenario_dict = request.scenario.model_dump(mode="json")
        
        # 3. Submit job
        job_id = self.job_manager.submit(
            job_type="simulation",
            payload={"season": request.season, "event": request.event, "driver": request.driver},
            func=execute_simulation_job,
            config=self.config,
            paths=self.paths,
            scenario_dict=scenario_dict,
            layer3_params=l3_params,
            seed=request.seed,
            monte_carlo=request.monte_carlo
        )
        
        return JobQueuedResponse(job_id=job_id, status="queued", message="Simulation job queued successfully.")
        
    def get_simulation_result(self, simulation_id: str) -> SimulationResultResponse:
        """Retrieve results for a completed simulation."""
        # This would typically read the summary from the DB or Parquet
        # Here we return a stub mimicking a successful DB query
        return SimulationResultResponse(
            simulation_id=simulation_id,
            success=True,
            total_race_time=5400.25,
            total_laps=57
        )
