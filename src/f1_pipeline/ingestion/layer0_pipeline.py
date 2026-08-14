from __future__ import annotations

import socket
from typing import Any

from f1_pipeline.core.config import load_config
from f1_pipeline.core.logging import configure_logging, get_logger
from f1_pipeline.core.paths import PATHS
from f1_pipeline.db.repositories.ingestion_runs import IngestionRunsRepository
from f1_pipeline.db.supabase_client import SupabaseConfigurationError, health_check
from f1_pipeline.ingestion.schemas import Layer0IngestionRequest, Layer0IngestionResult
from f1_pipeline.ingestion.services.fastf1_ingestion import FastF1IngestionService


LOGGER = get_logger(__name__)


class Layer0Pipeline:
    def __init__(
        self,
        *,
        ingestion_runs: IngestionRunsRepository | None = None,
        ingestion_service: FastF1IngestionService | None = None,
    ) -> None:
        self._injected_runs = ingestion_runs
        self._injected_service = ingestion_service

    def run(self, request: Layer0IngestionRequest) -> Layer0IngestionResult:
        config = load_config()
        configure_logging(config.log_level, log_file=PATHS.logs / "layer0_ingestion.log")
        LOGGER.info("Starting Layer 0 ingestion")

        ingestion_runs: IngestionRunsRepository | None = None
        run_id: str | None = None
        try:
            ingestion_runs = self._injected_runs or IngestionRunsRepository()
            health_check(ingestion_runs.client)
            run = ingestion_runs.create_started(
                season=request.season,
                event_name=request.event,
                session_type=request.session_type,
                driver_code=request.driver_code,
                config_hash=request.config_hash,
                code_version=request.code_version,
            )
            run_id = str(run["id"])
            LOGGER.info("Created ingestion run %s", run_id)

            ingestion_service = self._injected_service or FastF1IngestionService(
                raw_assets=None,
                config=config,
            )
            assets = ingestion_service.ingest(request=request, ingestion_run_id=run_id)
            ingestion_runs.mark_success(run_id)
            LOGGER.info("Layer 0 ingestion completed successfully")
            return Layer0IngestionResult(
                season=request.season,
                event=request.event,
                session_type=request.session_type,
                driver_code=request.driver_code,
                ingestion_run_id=run_id,
                assets=assets,
                success=True,
                message="Layer 0 ingestion completed successfully",
            )
        except Exception as exc:
            category, public_message = classify_error(exc)
            LOGGER.exception("%s: %s", category, public_message)
            if ingestion_runs is not None and run_id is not None:
                try:
                    ingestion_runs.mark_failed(run_id, public_message)
                except Exception:
                    LOGGER.exception("Failed to mark ingestion run as failed")
            return Layer0IngestionResult(
                season=request.season,
                event=request.event,
                session_type=request.session_type,
                driver_code=request.driver_code,
                ingestion_run_id=run_id,
                assets=[],
                success=False,
                message=f"{category}: {public_message}",
            )


def classify_error(exc: Exception) -> tuple[str, str]:
    text = str(exc)
    if isinstance(exc, SupabaseConfigurationError):
        return "configuration error", text
    if _chain_contains(exc, socket.gaierror) or _chain_text_contains(exc, "getaddrinfo failed"):
        return "DNS/network error", "Name resolution failed while connecting to an external service."
    if "Supabase" in text or "supabase" in text:
        return "Supabase connection error", text
    if "No laps found" in text or "Unsupported session" in text:
        return "FastF1 session error", text
    if "FastF1" in text or "fastf1" in text:
        return "FastF1 download error", "FastF1 could not load the requested session."
    if isinstance(exc, ValueError):
        return "validation error", text
    return "Layer 0 error", text or exc.__class__.__name__


def _chain_contains(exc: BaseException, expected_type: type[BaseException]) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, expected_type):
            return True
        current = current.__cause__ or current.__context__
    return False


def _chain_text_contains(exc: BaseException, needle: str) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if needle in str(current):
            return True
        current = current.__cause__ or current.__context__
    return False


def run_layer0_ingestion(request: Layer0IngestionRequest) -> Layer0IngestionResult:
    return Layer0Pipeline().run(request)
