from __future__ import annotations

from typing import Any

from supabase import Client

from f1_pipeline.db.supabase_client import get_supabase_client
from f1_pipeline.ingestion.schemas import RawAssetResult


class RepositoryError(RuntimeError):
    pass


class RawAssetsRepository:
    table_name = "raw_data_assets"

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_client()

    def create_asset(
        self,
        *,
        ingestion_run_id: str,
        source: str,
        asset_type: str,
        season: int,
        event_name: str,
        session_type: str,
        driver_code: str | None,
        lap_number: int | None,
        storage_path: str,
        file_format: str,
        checksum: str,
        row_count: int | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ingestion_run_id": ingestion_run_id,
            "source": source,
            "asset_type": asset_type,
            "season": season,
            "event_name": event_name,
            "session_type": session_type,
            "driver_code": driver_code,
            "lap_number": lap_number,
            "storage_path": storage_path,
            "file_format": file_format,
            "checksum": checksum,
            "row_count": row_count,
        }
        return self._execute_single(lambda: self.client.table(self.table_name).insert(payload).execute().data)

    def create_from_result(self, *, ingestion_run_id: str, asset: RawAssetResult) -> dict[str, Any]:
        return self.create_asset(
            ingestion_run_id=ingestion_run_id,
            source=asset.source,
            asset_type=asset.asset_type,
            season=asset.season,
            event_name=asset.event,
            session_type=asset.session_type,
            driver_code=asset.driver_code,
            lap_number=asset.lap_number,
            storage_path=asset.storage_path,
            file_format=asset.file_format,
            checksum=asset.checksum,
            row_count=asset.row_count,
        )

    def get_assets_for_run(self, ingestion_run_id: str) -> list[dict[str, Any]]:
        try:
            return (
                self.client.table(self.table_name)
                .select("*")
                .eq("ingestion_run_id", ingestion_run_id)
                .execute()
                .data
            )
        except Exception as exc:
            raise RepositoryError("Supabase raw_data_assets lookup failed.") from exc

    def find_existing_asset(
        self,
        *,
        source: str,
        asset_type: str,
        season: int,
        event_name: str,
        session_type: str,
        driver_code: str | None,
    ) -> dict[str, Any] | None:
        query = (
            self.client.table(self.table_name)
            .select("*")
            .eq("source", source)
            .eq("asset_type", asset_type)
            .eq("season", season)
            .eq("event_name", event_name)
            .eq("session_type", session_type)
        )
        query = query.is_("driver_code", "null") if driver_code is None else query.eq("driver_code", driver_code)
        try:
            rows = query.order("created_at", desc=True).limit(1).execute().data
        except Exception as exc:
            raise RepositoryError("Supabase raw_data_assets duplicate lookup failed.") from exc
        return rows[0] if rows else None

    def find_assets(
        self,
        *,
        season: int,
        event_name: str,
        session_type: str,
        driver_code: str | None = None,
        asset_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query raw assets matching the given filters.

        Used by Layer 1 to discover Layer 0 outputs for normalization.
        """
        query = (
            self.client.table(self.table_name)
            .select("*")
            .eq("season", season)
            .eq("event_name", event_name)
            .eq("session_type", session_type)
        )
        if driver_code is not None:
            query = query.eq("driver_code", driver_code)
        if asset_type is not None:
            query = query.eq("asset_type", asset_type)
        try:
            return query.order("created_at", desc=True).execute().data
        except Exception as exc:
            raise RepositoryError("Supabase raw_data_assets query failed.") from exc

    @staticmethod
    def _single(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            raise RepositoryError("Supabase raw_data_assets operation returned no rows.")
        return rows[0]

    def _execute_single(self, operation: Any) -> dict[str, Any]:
        try:
            return self._single(operation())
        except Exception as exc:
            raise RepositoryError("Supabase raw_data_assets operation failed.") from exc


RawAssetRepository = RawAssetsRepository
