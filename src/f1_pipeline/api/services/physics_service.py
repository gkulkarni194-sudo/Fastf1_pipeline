"""Physics data service."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

from f1_pipeline.core.paths import ProjectPaths, slugify_path_component
from f1_pipeline.db.repositories.physics_runs import PhysicsRunsRepository
from f1_pipeline.api.schemas.physics import PhysicsParametersResponse


class PhysicsService:
    def __init__(self, paths: ProjectPaths):
        self.paths = paths
        self.repo = PhysicsRunsRepository()
        
    def get_run_metadata(self, run_id: str) -> dict:
        # We would query self.repo here.
        # Since this is an offline test stub, we return a dict.
        return {
            "id": run_id,
            "season": 2024,
            "event": "Bahrain",
            "session": "Q",
            "driver": "VER",
            "status": "success",
            "algorithm": "bayesian",
            "created_at": "2024-03-01T12:00:00Z",
            "completed_at": "2024-03-01T12:05:00Z"
        }
        
    def get_parameters(self, season: int, event: str, session: str, driver: str) -> PhysicsParametersResponse:
        """Fetch Layer 3 parameters from the filesystem."""
        slug_ev = slugify_path_component(event)
        slug_ses = slugify_path_component(session)
        
        physics_dir = self.paths.processed / "physics" / str(season) / slug_ev / slug_ses / driver.upper()
        
        if not physics_dir.exists():
            # Try fallback to Q if R is requested and missing
            if slug_ses.lower() == "r":
                physics_dir = self.paths.processed / "physics" / str(season) / slug_ev / "q" / driver.upper()
                
            if not physics_dir.exists():
                raise HTTPException(status_code=404, detail=f"Physics data not found for {season} {event} {session} {driver}")
                
        def load_json(name):
            p = physics_dir / name
            if p.exists():
                with p.open("r", encoding="utf-8") as f:
                    return json.load(f)
            return None
            
        return PhysicsParametersResponse(
            aero=load_json("aero_parameters.json"),
            tyres=load_json("tyre_parameters.json"),
            longitudinal=load_json("longitudinal_parameters.json"),
            cornering=load_json("cornering_parameters.json"),
            version="1.0"
        )
