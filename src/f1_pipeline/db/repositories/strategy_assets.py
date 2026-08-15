"""Strategy assets repository."""
from __future__ import annotations

import logging

from supabase import Client
from f1_pipeline.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class StrategyAssetsRepository:
    """Repository for managing strategy assets and definitions in Supabase."""

    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def create_asset(
        self,
        run_id: str,
        asset_type: str,
        file_path: str,
        checksum: str,
        file_format: str = "parquet",
        row_count: int | None = None,
    ) -> str:
        """Register a new strategy asset (e.g., ranked strategies, sensitivity)."""
        data = {
            "strategy_run_id": run_id,
            "asset_type": asset_type,
            "storage_path": str(file_path),
            "file_format": file_format,
            "checksum": checksum,
            "row_count": row_count
        }
        response = self.client.table("strategy_assets").insert(data).execute()
        return response.data[0]["id"]
        
    def find_strategy_by_hash(self, strategy_hash: str) -> str | None:
        """Find if a strategy definition already exists."""
        response = self.client.table("strategy_definitions").select("id").eq("strategy_hash", strategy_hash).execute()
        if response.data:
            return response.data[0]["id"]
        return None
        
    def create_strategy_definition(self, strategy_hash: str, strategy_json: dict) -> str:
        """Upsert a strategy definition."""
        existing = self.find_strategy_by_hash(strategy_hash)
        if existing:
            return existing
            
        data = {
            "strategy_hash": strategy_hash,
            "strategy_json": strategy_json
        }
        response = self.client.table("strategy_definitions").insert(data).execute()
        return response.data[0]["id"]
        
    def create_strategy_result(self, run_id: str, strategy_hash: str, result_data: dict) -> str:
        """Store the optimization result for a specific strategy."""
        data = {
            "strategy_run_id": run_id,
            "strategy_hash": strategy_hash,
            **result_data
        }
        response = self.client.table("strategy_results").insert(data).execute()
        return response.data[0]["id"]
