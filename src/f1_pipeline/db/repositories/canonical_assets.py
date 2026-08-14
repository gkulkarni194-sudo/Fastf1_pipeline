from __future__ import annotations

from typing import Any

from supabase import Client

from f1_pipeline.db.supabase_client import get_supabase_client


class CanonicalAssetsRepository:
    """CRUD operations for the ``canonical_assets`` Supabase table."""

    table_name = "canonical_assets"

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_client()

    def create_asset(
        self,
        *,
        normalization_run_id: str,
        source_asset_id: str | None,
        season: int,
        event_name: str,
        session_type: str,
        driver_code: str | None,
        asset_type: str,
        storage_path: str,
        file_format: str,
        checksum: str,
        row_count: int | None,
        schema_version: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "normalization_run_id": normalization_run_id,
            "source_asset_id": source_asset_id,
            "season": season,
            "event_name": event_name,
            "session_type": session_type,
            "driver_code": driver_code,
            "asset_type": asset_type,
            "storage_path": storage_path,
            "file_format": file_format,
            "checksum": checksum,
            "row_count": row_count,
            "schema_version": schema_version,
        }
        rows = self.client.table(self.table_name).insert(payload).execute().data
        if not rows:
            raise RuntimeError("Supabase canonical_assets insert returned no rows.")
        return rows[0]

    def find_existing(
        self,
        *,
        source_asset_id: str,
        schema_version: str,
    ) -> dict[str, Any] | None:
        """Return an existing canonical asset for the given source + schema version."""
        rows = (
            self.client.table(self.table_name)
            .select("*")
            .eq("source_asset_id", source_asset_id)
            .eq("schema_version", schema_version)
            .limit(1)
            .execute()
            .data
        )
        return rows[0] if rows else None

    def get_assets_for_run(self, normalization_run_id: str) -> list[dict[str, Any]]:
        return (
            self.client.table(self.table_name)
            .select("*")
            .eq("normalization_run_id", normalization_run_id)
            .execute()
            .data
        )
