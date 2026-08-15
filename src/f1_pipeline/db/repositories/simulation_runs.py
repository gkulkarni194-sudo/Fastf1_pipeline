"""Repository for Simulation runs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from postgrest.base_request_builder import APIResponse

from f1_pipeline.db.supabase_client import get_supabase_client


class SimulationRunsRepository:
    def __init__(self):
        self.client = get_supabase_client()

    def create_started(self, season: int, event: str, session: str, driver: str, scenario_hash: str) -> str:
        """Create a new started run record and return its UUID."""
        data = {
            "season": season,
            "event_slug": event,
            "session_slug": session,
            "driver_code": driver,
            "scenario_hash": scenario_hash,
            "status": "started",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        
        response: APIResponse = self.client.table("simulation_runs").insert(data).execute()
        
        if not response.data:
            raise RuntimeError("Failed to create simulation run record")
            
        return str(response.data[0]["id"])

    def mark_success(self, run_id: str, results_summary: dict[str, Any]) -> None:
        """Mark a run as successful and save the summary."""
        data = {
            "status": "success",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "results_summary": results_summary,
        }
        
        self.client.table("simulation_runs").update(data).eq("id", run_id).execute()

    def mark_failed(self, run_id: str, error_message: str) -> None:
        """Mark a run as failed."""
        data = {
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error_message": error_message,
        }
        
        self.client.table("simulation_runs").update(data).eq("id", run_id).execute()
