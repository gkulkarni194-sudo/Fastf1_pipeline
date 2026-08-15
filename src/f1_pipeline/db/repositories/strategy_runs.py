"""Strategy runs repository."""
from __future__ import annotations

import logging
from typing import Any

from supabase import Client
from f1_pipeline.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class StrategyRunsRepository:
    """Repository for managing strategy optimization runs in Supabase."""

    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def create_started(
        self,
        algorithm: str,
        objective: str,
        config_hash: str,
        strategy_schema_version: str = "1.0",
        source_simulation_context_id: str | None = None
    ) -> str:
        """Create a new strategy optimization run record."""
        data = {
            "status": "started",
            "algorithm": algorithm,
            "objective": objective,
            "config_hash": config_hash,
            "strategy_schema_version": strategy_schema_version,
            "source_simulation_context_id": source_simulation_context_id
        }
        
        response = self.client.table("strategy_runs").insert(data).execute()
        return response.data[0]["id"]

    def mark_success(self, run_id: str) -> None:
        """Mark an optimization run as successful."""
        data = {
            "status": "success",
            "completed_at": "now()"
        }
        self.client.table("strategy_runs").update(data).eq("id", run_id).execute()

    def mark_failed(self, run_id: str, error_message: str) -> None:
        """Mark an optimization run as failed."""
        data = {
            "status": "failed",
            "error_message": error_message,
            "completed_at": "now()"
        }
        self.client.table("strategy_runs").update(data).eq("id", run_id).execute()
