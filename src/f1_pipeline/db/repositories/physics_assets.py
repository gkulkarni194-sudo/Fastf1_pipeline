from __future__ import annotations

from typing import Any

from supabase import Client

from f1_pipeline.db.supabase_client import get_supabase_client


class PhysicsAssetsRepository:
    table_name = "physics_assets"
    parameter_table_name = "physics_parameters"

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_client()

    def create_asset(
        self,
        *,
        source_feature_asset_id: str | None,
        season: int,
        event_name: str,
        session_type: str,
        driver_code: str | None,
        asset_type: str,
        storage_path: str,
        file_format: str,
        checksum: str,
        row_count: int | None,
        physics_schema_version: str,
    ) -> dict[str, Any]:
        payload = {
            "source_feature_asset_id": source_feature_asset_id,
            "season": season,
            "event_name": event_name,
            "session_type": session_type,
            "driver_code": driver_code,
            "asset_type": asset_type,
            "storage_path": storage_path,
            "file_format": file_format,
            "checksum": checksum,
            "row_count": row_count,
            "physics_schema_version": physics_schema_version,
        }
        rows = self.client.table(self.table_name).insert(payload).execute().data
        if not rows:
            raise RuntimeError("Supabase physics_assets insert returned no rows.")
        return rows[0]

    def create_parameter(
        self,
        *,
        physics_run_id: str,
        parameter_name: str,
        value: float | None,
        unit: str,
        standard_error: float | None,
        confidence_interval_low: float | None,
        confidence_interval_high: float | None,
        model_name: str,
        model_version: str,
        sample_count: int,
        status: str,
    ) -> dict[str, Any]:
        payload = {
            "physics_run_id": physics_run_id,
            "parameter_name": parameter_name,
            "value": value,
            "unit": unit,
            "standard_error": standard_error,
            "confidence_interval_low": confidence_interval_low,
            "confidence_interval_high": confidence_interval_high,
            "model_name": model_name,
            "model_version": model_version,
            "sample_count": sample_count,
            "status": status,
        }
        rows = self.client.table(self.parameter_table_name).insert(payload).execute().data
        if not rows:
            raise RuntimeError("Supabase physics_parameters insert returned no rows.")
        return rows[0]

    def find_existing(
        self,
        *,
        source_feature_asset_id: str | None,
        asset_type: str,
        physics_schema_version: str,
    ) -> dict[str, Any] | None:
        query = (
            self.client.table(self.table_name)
            .select("*")
            .eq("asset_type", asset_type)
            .eq("physics_schema_version", physics_schema_version)
        )
        if source_feature_asset_id is None:
            query = query.is_("source_feature_asset_id", "null")
        else:
            query = query.eq("source_feature_asset_id", source_feature_asset_id)
        rows = query.limit(1).execute().data
        return rows[0] if rows else None
