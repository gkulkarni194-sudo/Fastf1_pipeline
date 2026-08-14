from __future__ import annotations

from typing import Any
from supabase import Client
from f1_pipeline.db.supabase_client import get_supabase_client


class FeatureAssetsRepository:
    """CRUD operations for the ``feature_assets`` Supabase table."""

    table_name = "feature_assets"

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_client()

    def create_asset(
        self,
        *,
        feature_run_id: str,
        source_canonical_asset_id: str,
        season: int,
        event_name: str,
        session_type: str,
        driver_code: str | None,
        asset_type: str,
        storage_path: str,
        file_format: str,
        checksum: str,
        row_count: int | None,
        feature_schema_version: str,
        config_hash: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "feature_run_id": feature_run_id,
            "source_canonical_asset_id": source_canonical_asset_id,
            "season": season,
            "event_name": event_name,
            "session_type": session_type,
            "driver_code": driver_code,
            "asset_type": asset_type,
            "storage_path": storage_path,
            "file_format": file_format,
            "checksum": checksum,
            "row_count": row_count,
            "feature_schema_version": feature_schema_version,
            "config_hash": config_hash,
        }
        rows = self.client.table(self.table_name).insert(payload).execute().data
        if not rows:
            raise RuntimeError("Supabase feature_assets insert returned no rows.")
        return rows[0]

    def find_existing(
        self,
        *,
        source_canonical_asset_id: str,
        feature_schema_version: str,
        config_hash: str | None = None,
    ) -> dict[str, Any] | None:
        """Return an existing feature asset for the idempotency triple.

        Triple: source_canonical_asset_id + feature_schema_version + config_hash.
        """
        query = (
            self.client.table(self.table_name)
            .select("*")
            .eq("source_canonical_asset_id", source_canonical_asset_id)
            .eq("feature_schema_version", feature_schema_version)
        )
        if config_hash is not None:
            query = query.eq("config_hash", config_hash)
        else:
            query = query.is_("config_hash", "null")
        rows = query.limit(1).execute().data
        return rows[0] if rows else None

    def get_assets_for_run(self, feature_run_id: str) -> list[dict[str, Any]]:
        return (
            self.client.table(self.table_name)
            .select("*")
            .eq("feature_run_id", feature_run_id)
            .execute()
            .data
        )
