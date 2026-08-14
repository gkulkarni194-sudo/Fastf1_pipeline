from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from supabase import Client

from f1_pipeline.db.supabase_client import get_supabase_client


class NormalizationRunsRepository:
    """CRUD operations for the ``normalization_runs`` Supabase table."""

    table_name = "normalization_runs"

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_client()

    def create_started(
        self,
        *,
        source_ingestion_run_id: str | None = None,
        config_hash: str | None = None,
        code_version: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_ingestion_run_id": source_ingestion_run_id,
            "status": "started",
            "started_at": _utc_now_iso(),
            "completed_at": None,
            "error_message": None,
            "config_hash": config_hash,
            "code_version": code_version,
        }
        return self._single(
            self.client.table(self.table_name).insert(payload).execute().data
        )

    def mark_success(self, run_id: str) -> dict[str, Any]:
        payload = {
            "status": "success",
            "completed_at": _utc_now_iso(),
            "error_message": None,
        }
        return self._single(
            self.client.table(self.table_name)
            .update(payload)
            .eq("id", run_id)
            .execute()
            .data
        )

    def mark_failed(self, run_id: str, error_message: str) -> dict[str, Any]:
        payload = {
            "status": "failed",
            "completed_at": _utc_now_iso(),
            "error_message": error_message,
        }
        return self._single(
            self.client.table(self.table_name)
            .update(payload)
            .eq("id", run_id)
            .execute()
            .data
        )

    def get_by_id(self, run_id: str) -> dict[str, Any] | None:
        rows = (
            self.client.table(self.table_name)
            .select("*")
            .eq("id", run_id)
            .execute()
            .data
        )
        return rows[0] if rows else None

    # ------------------------------------------------------------------
    @staticmethod
    def _single(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            raise RuntimeError("Supabase normalization_runs operation returned no rows.")
        return rows[0]


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
