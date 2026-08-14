from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from f1_pipeline.core.config import RuntimeConfig, load_config
from f1_pipeline.core.logging import get_logger
from f1_pipeline.core.paths import PROJECT_ROOT, fastf1_raw_session_dir
from f1_pipeline.db.repositories.raw_assets import RawAssetsRepository
from f1_pipeline.ingestion.clients.fastf1_client import FastF1Client
from f1_pipeline.ingestion.quality import (
    raise_if_failed,
    validate_laps,
    validate_telemetry,
    validate_weather,
)
from f1_pipeline.ingestion.schemas import Layer0IngestionRequest, RawAssetResult
from f1_pipeline.ingestion.storage import StorageManager, StoredAsset


LOGGER = get_logger(__name__)


class FastF1IngestionService:
    def __init__(
        self,
        *,
        fastf1_client: FastF1Client | None = None,
        storage: StorageManager | None = None,
        raw_assets: RawAssetsRepository | None = None,
        config: RuntimeConfig | None = None,
    ) -> None:
        self.config = config or load_config()
        self.fastf1_client = fastf1_client or FastF1Client(config=self.config)
        self.storage = storage or StorageManager()
        self.raw_assets = raw_assets or RawAssetsRepository()
        self.raw_root = self.config.raw_fastf1_root

    def ingest(self, *, request: Layer0IngestionRequest, ingestion_run_id: str) -> list[RawAssetResult]:
        LOGGER.info("Loading FastF1 session %s %s %s", request.season, request.event, request.session_type)
        session = self.fastf1_client.load_session(request.season, request.event, request.session_type)

        output_dir = fastf1_raw_session_dir(
            season=request.season,
            event=request.event,
            session_type=request.session_type,
            driver_code=request.driver_code,
            raw_root=self.raw_root,
        )
        assets: list[RawAssetResult] = []

        laps = _safe_dataframe(session.laps)
        report = validate_laps(laps)
        raise_if_failed(report)
        assets.append(
            self._save_asset(
                dataframe=laps,
                path=output_dir / "laps.parquet",
                request=request,
                ingestion_run_id=ingestion_run_id,
                asset_type="fastf1_session_laps",
            )
        )

        weather = _safe_dataframe(getattr(session, "weather_data", pd.DataFrame()))
        weather_report = validate_weather(weather)
        if weather_report.warnings:
            LOGGER.warning("; ".join(weather_report.warnings))
        if not weather.empty:
            assets.append(
                self._save_asset(
                    dataframe=weather,
                    path=output_dir / "weather.parquet",
                    request=request,
                    ingestion_run_id=ingestion_run_id,
                    asset_type="fastf1_weather",
                )
            )

        if request.driver_code:
            telemetry, lap_number = self._driver_telemetry(session, request.driver_code)
            telemetry_report = validate_telemetry(telemetry)
            for warning in telemetry_report.warnings:
                LOGGER.warning(warning)
            raise_if_failed(telemetry_report)
            assets.append(
                self._save_asset(
                    dataframe=telemetry,
                    path=output_dir / "telemetry.parquet",
                    request=request,
                    ingestion_run_id=ingestion_run_id,
                    asset_type="fastf1_driver_telemetry",
                    lap_number=lap_number,
                )
            )

        metadata = self._session_metadata(session, request, [asset.asset_type for asset in assets])
        assets.append(
            self._save_metadata(
                payload=metadata,
                path=output_dir / "metadata.json",
                request=request,
                ingestion_run_id=ingestion_run_id,
            )
        )
        return assets

    def _save_asset(
        self,
        *,
        dataframe: pd.DataFrame,
        path: Path,
        request: Layer0IngestionRequest,
        ingestion_run_id: str,
        asset_type: str,
        lap_number: int | None = None,
    ) -> RawAssetResult:
        existing = self._existing_asset(request=request, asset_type=asset_type)
        if existing and _local_file_exists(existing.get("storage_path")) and not request.force:
            LOGGER.info("Reusing existing raw asset %s at %s", asset_type, existing.get("storage_path"))
            return self._asset_result_from_row(existing)

        LOGGER.info("Saving raw asset %s to %s", asset_type, path)
        stored = self.storage.save_dataframe(dataframe, path)
        asset = self._asset_result(stored, request=request, asset_type=asset_type, lap_number=lap_number)
        self.raw_assets.create_from_result(ingestion_run_id=ingestion_run_id, asset=asset)
        return asset

    def _save_metadata(
        self,
        *,
        payload: dict[str, Any],
        path: Path,
        request: Layer0IngestionRequest,
        ingestion_run_id: str,
    ) -> RawAssetResult:
        asset_type = "fastf1_session_metadata"
        existing = self._existing_asset(request=request, asset_type=asset_type)
        if existing and _local_file_exists(existing.get("storage_path")) and not request.force:
            return self._asset_result_from_row(existing)
        stored = self.storage.save_json(payload, path)
        asset = self._asset_result(stored, request=request, asset_type=asset_type)
        self.raw_assets.create_from_result(ingestion_run_id=ingestion_run_id, asset=asset)
        return asset

    def _existing_asset(self, *, request: Layer0IngestionRequest, asset_type: str) -> dict[str, Any] | None:
        return self.raw_assets.find_existing_asset(
            source="fastf1",
            asset_type=asset_type,
            season=request.season,
            event_name=request.event,
            session_type=request.session_type,
            driver_code=request.driver_code,
        )

    def _asset_result(
        self,
        stored: StoredAsset,
        *,
        request: Layer0IngestionRequest,
        asset_type: str,
        lap_number: int | None = None,
    ) -> RawAssetResult:
        return RawAssetResult(
            source="fastf1",
            asset_type=asset_type,
            season=request.season,
            event=request.event,
            session_type=request.session_type,
            driver_code=request.driver_code,
            lap_number=lap_number,
            storage_path=stored.path,
            file_format=stored.file_format,
            checksum=stored.checksum,
            row_count=stored.row_count,
        )

    def _asset_result_from_row(self, row: dict[str, Any]) -> RawAssetResult:
        return RawAssetResult(
            source=str(row["source"]),
            asset_type=str(row["asset_type"]),
            season=int(row["season"]),
            event=str(row["event_name"]),
            session_type=str(row["session_type"]),
            driver_code=row.get("driver_code"),
            lap_number=row.get("lap_number"),
            storage_path=str(row["storage_path"]),
            file_format=str(row["file_format"]),
            checksum=str(row["checksum"]),
            row_count=row.get("row_count"),
        )

    def _driver_telemetry(self, session: Any, driver_code: str) -> tuple[pd.DataFrame, int | None]:
        laps = session.laps
        driver_laps = (
            laps.pick_drivers(driver_code)
            if hasattr(laps, "pick_drivers")
            else laps.pick_driver(driver_code)
        )
        if driver_laps.empty:
            raise ValueError(f"No laps found for driver {driver_code}.")

        lap = driver_laps.pick_fastest()
        lap_number = int(lap["LapNumber"]) if pd.notna(lap["LapNumber"]) else None
        telemetry = _safe_dataframe(lap.get_car_data())
        telemetry["Driver"] = driver_code
        if lap_number is not None:
            telemetry["LapNumber"] = lap_number
        return telemetry, lap_number

    @staticmethod
    def _session_metadata(
        session: Any,
        request: Layer0IngestionRequest,
        asset_types: list[str],
    ) -> dict[str, Any]:
        event = getattr(session, "event", None)
        return {
            "source": "fastf1",
            "season": request.season,
            "event": request.event,
            "session_type": request.session_type,
            "driver_code": request.driver_code,
            "fastf1_event": _json_safe(event.to_dict() if hasattr(event, "to_dict") else event),
            "saved_asset_types": asset_types,
        }


def _safe_dataframe(value: Any) -> pd.DataFrame:
    return pd.DataFrame(value).copy()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _slug(value: str) -> str:
    """Backward-compatible wrapper — use ``f1_pipeline.core.text.slug``."""
    from f1_pipeline.core.text import slug
    return slug(value)


def _local_file_exists(storage_path: Any) -> bool:
    if not storage_path:
        return False
    path = Path(str(storage_path))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.exists()


FastF1Layer0IngestionService = FastF1IngestionService
