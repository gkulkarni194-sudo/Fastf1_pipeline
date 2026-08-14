from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from supabase import Client
from f1_pipeline.db.supabase_client import get_supabase_client
from f1_pipeline.features.schemas import FEATURE_SCHEMA_VERSION


class FeatureRunsRepository:
    """CRUD operations for the ``feature_runs`` Supabase table."""

    table_name = "feature_runs"

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_client()

    def create_started(
        self,
        *,
        source_normalization_run_id: str,
        config_hash: str | None = None,
        code_version: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_normalization_run_id": source_normalization_run_id,
            "status": "started",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "config_hash": config_hash,
            "code_version": code_version,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
        }
        rows = self.client.table(self.table_name).insert(payload).execute().data
        if not rows:
            raise RuntimeError("Supabase feature_runs insert returned no rows.")
        return rows[0]

    def mark_success(self, run_id: str) -> dict[str, Any]:
        payload = {
            "status": "success",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        rows = (
            self.client.table(self.table_name)
            .update(payload)
            .eq("id", run_id)
            .execute()
            .data
        )
        if not rows:
            raise RuntimeError(f"Could not update feature_run {run_id} to success.")
        return rows[0]

    def mark_failed(self, run_id: str, error_message: str) -> dict[str, Any]:
        payload = {
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error_message": error_message,
        }
        rows = (
            self.client.table(self.table_name)
            .update(payload)
            .eq("id", run_id)
            .execute()
            .data
        )
        if not rows:
            raise RuntimeError(f"Could not update feature_run {run_id} to failed.")
        return rows[0]
