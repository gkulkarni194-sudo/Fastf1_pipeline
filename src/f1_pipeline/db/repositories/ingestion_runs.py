from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from supabase import Client

from f1_pipeline.db.supabase_client import get_supabase_client


class RepositoryError(RuntimeError):
    pass


class IngestionRunsRepository:
    table_name = "ingestion_runs"

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_client()

    def create_started(
        self,
        *,
        season: int,
        event_name: str,
        session_type: str,
        driver_code: str | None = None,
        config_hash: str | None = None,
        code_version: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "season": season,
            "event_name": event_name,
            "session_type": session_type,
            "driver_code": driver_code,
            "status": "started",
            "started_at": _utc_now_iso(),
            "completed_at": None,
            "error_message": None,
            "config_hash": config_hash,
            "code_version": code_version,
        }
        return self._execute_single(lambda: self.client.table(self.table_name).insert(payload).execute().data)

    def mark_success(self, run_id: str) -> dict[str, Any]:
        payload = {
            "status": "success",
            "completed_at": _utc_now_iso(),
            "error_message": None,
        }
        return self._execute_single(
            lambda: self.client.table(self.table_name).update(payload).eq("id", run_id).execute().data
        )

    def mark_failed(self, run_id: str, error_message: str) -> dict[str, Any]:
        payload = {
            "status": "failed",
            "completed_at": _utc_now_iso(),
            "error_message": error_message,
        }
        return self._execute_single(
            lambda: self.client.table(self.table_name).update(payload).eq("id", run_id).execute().data
        )

    def get_by_id(self, run_id: str) -> dict[str, Any] | None:
        try:
            rows = (
                self.client.table(self.table_name)
                .select("*")
                .eq("id", run_id)
                .limit(1)
                .execute()
                .data
            )
        except Exception as exc:
            raise RepositoryError("Supabase ingestion_runs lookup failed.") from exc
        return rows[0] if rows else None

    @staticmethod
    def _single(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            raise RuntimeError("Supabase operation returned no rows.")
        return rows[0]

    def _execute_single(self, operation: Any) -> dict[str, Any]:
        try:
            return self._single(operation())
        except Exception as exc:
            raise RepositoryError("Supabase ingestion_runs operation failed.") from exc


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


IngestionRunRepository = IngestionRunsRepository
