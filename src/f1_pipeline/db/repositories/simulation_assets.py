"""Repository for Simulation assets."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from f1_pipeline.db.supabase_client import get_supabase_client


class SimulationAssetsRepository:
    def __init__(self):
        self.client = get_supabase_client()

    def create_asset(self, run_id: str, asset_type: str, file_path: str, checksum: str, file_format: str, row_count: int | None = None) -> None:
        """Register a simulation output asset."""
        data = {
            "simulation_run_id": run_id,
            "asset_type": asset_type,
            "storage_path": file_path,
            "checksum": checksum,
            "file_format": file_format,
            "row_count": row_count,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        self.client.table("simulation_assets").insert(data).execute()
        
    def find_scenario_by_hash(self, scenario_hash: str) -> str | None:
        """Find an existing scenario by its hash, returning its ID if found."""
        response = self.client.table("simulation_scenarios").select("id").eq("scenario_hash", scenario_hash).execute()
        if response.data:
            return str(response.data[0]["id"])
        return None
        
    def create_scenario(self, scenario_hash: str, scenario_data: dict[str, Any]) -> str:
        """Store a scenario definition and return its ID."""
        data = {
            "scenario_hash": scenario_hash,
            "scenario_data": scenario_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        response = self.client.table("simulation_scenarios").insert(data).execute()
        if not response.data:
            raise RuntimeError("Failed to create simulation scenario record")
            
        return str(response.data[0]["id"])
