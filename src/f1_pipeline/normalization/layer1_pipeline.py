"""Layer 1 pipeline — canonical data normalization.

Workflow
--------
1. Validate configuration.
2. Test Supabase connectivity.
3. Query ``raw_data_assets`` for successful Layer 0 assets.
4. Create ``normalization_run`` with status = started.
5. For each raw asset:
   a. Check idempotency — skip if already normalized with same schema version.
   b. Load & canonicalize.
   c. Save canonical Parquet under ``data/interim/canonical/``.
   d. Register ``canonical_asset`` in Supabase.
6. Save normalization metadata JSON.
7. Mark ``normalization_run`` = success.
8. Return ``Layer1NormalizationResult``.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from f1_pipeline.core.hashing import file_sha256
from f1_pipeline.core.paths import PATHS, PROJECT_ROOT
from f1_pipeline.core.text import slug
from f1_pipeline.db.repositories.canonical_assets import CanonicalAssetsRepository
from f1_pipeline.db.repositories.normalization_runs import NormalizationRunsRepository
from f1_pipeline.db.repositories.raw_assets import RawAssetsRepository
from f1_pipeline.ingestion.storage import StorageManager
from f1_pipeline.normalization.canonicalizer import (
    canonicalize_laps,
    canonicalize_telemetry,
    canonicalize_weather,
)
from f1_pipeline.normalization.loaders import load_raw_parquet
from f1_pipeline.normalization.schemas import (
    CANONICAL_SCHEMA_VERSION,
    CanonicalAssetResult,
    Layer1NormalizationRequest,
    Layer1NormalizationResult,
    QualityReport,
)

logger = logging.getLogger(__name__)

# Map raw_data_assets.asset_type → Layer 1 canonical asset type
_RAW_TO_CANONICAL: dict[str, str] = {
    "fastf1_session_laps": "laps",
    "fastf1_weather": "weather",
    "fastf1_driver_telemetry": "telemetry",
}

# Reverse: requested asset type → raw_data_assets.asset_type patterns
_REQUESTED_TO_RAW: dict[str, list[str]] = {
    "laps": ["fastf1_session_laps"],
    "weather": ["fastf1_weather"],
    "telemetry": ["fastf1_driver_telemetry"],
}


def _supabase_hostname() -> str:
    url = os.getenv("SUPABASE_URL", "")
    try:
        return urlparse(url).hostname or "<not set>"
    except Exception:
        return "<invalid url>"


def _canonical_output_dir(
    season: int, event: str, session_type: str,
) -> Path:
    """Build the canonical output directory."""
    return (
        PATHS.interim / "canonical"
        / str(season) / slug(event) / slug(session_type)
    )


def _clean_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


class Layer1Pipeline:
    def __init__(
        self,
        *,
        raw_assets: RawAssetsRepository | None = None,
        canonical_assets: CanonicalAssetsRepository | None = None,
        normalization_runs: NormalizationRunsRepository | None = None,
        storage: StorageManager | None = None,
    ) -> None:
        self._raw_assets = raw_assets
        self._canonical_assets = canonical_assets
        self._normalization_runs = normalization_runs
        self._storage = storage

    def run(self, request: Layer1NormalizationRequest) -> Layer1NormalizationResult:
        # ---------------------------------------------------------------
        # Phase 1 — Supabase connectivity
        # ---------------------------------------------------------------
        try:
            raw_assets_repo = self._raw_assets or RawAssetsRepository()
            canonical_repo = self._canonical_assets or CanonicalAssetsRepository()
            norm_runs_repo = self._normalization_runs or NormalizationRunsRepository()
            storage = self._storage or StorageManager()
            logger.info("Supabase host: %s", _supabase_hostname())
        except Exception as exc:
            logger.error("Supabase connection failed: %s", exc)
            return Layer1NormalizationResult(
                success=False,
                message=f"Supabase connection failed: {exc}",
            )

        # ---------------------------------------------------------------
        # Phase 2 — Discover Layer 0 assets
        # ---------------------------------------------------------------
        try:
            raw_rows = raw_assets_repo.find_assets(
                season=request.season,
                event_name=request.event,
                session_type=request.session_type,
                driver_code=request.driver_code,
            )
        except Exception as exc:
            logger.error("Failed to query raw assets: %s", exc)
            return Layer1NormalizationResult(
                success=False,
                message=f"Raw asset discovery failed: {exc}",
            )

        if not raw_rows:
            return Layer1NormalizationResult(
                success=False,
                message=(
                    f"No Layer 0 assets found for "
                    f"{request.season}/{request.event}/{request.session_type}"
                    f"/{request.driver_code or 'all'}."
                ),
            )

        # Filter to requested asset types
        wanted_raw_types: set[str] = set()
        for at in request.asset_types:
            wanted_raw_types.update(_REQUESTED_TO_RAW.get(at, []))

        raw_rows = [r for r in raw_rows if r.get("asset_type") in wanted_raw_types]
        if not raw_rows:
            return Layer1NormalizationResult(
                success=False,
                message="No matching Layer 0 assets for requested asset types.",
            )

        # Find the source ingestion run id (from the first asset)
        source_run_id = raw_rows[0].get("ingestion_run_id")

        # ---------------------------------------------------------------
        # Phase 3 — Create normalization run
        # ---------------------------------------------------------------
        try:
            norm_run = norm_runs_repo.create_started(
                source_ingestion_run_id=source_run_id,
                config_hash=request.config_hash,
                code_version=request.code_version,
            )
            norm_run_id = str(norm_run["id"])
            logger.info("Normalization run created: %s", norm_run_id)
        except Exception as exc:
            logger.error("Failed to create normalization run: %s", exc)
            return Layer1NormalizationResult(
                success=False,
                message=f"Failed to create normalization run: {exc}",
            )

        # ---------------------------------------------------------------
        # Phase 4 — Process each raw asset
        # ---------------------------------------------------------------
        assets: list[CanonicalAssetResult] = []
        skipped: list[str] = []
        quality_reports: list[QualityReport] = []
        duplicate_reports: list[Any] = []

        try:
            output_dir = _canonical_output_dir(
                request.season, request.event, request.session_type,
            )
            output_dir.mkdir(parents=True, exist_ok=True)

            for raw_row in raw_rows:
                raw_asset_type = raw_row["asset_type"]
                canonical_type = _RAW_TO_CANONICAL.get(raw_asset_type)
                if canonical_type is None:
                    logger.warning("Unknown raw asset type: %s — skipping", raw_asset_type)
                    skipped.append(f"unknown:{raw_asset_type}")
                    continue

                source_asset_id = str(raw_row["id"])
                storage_path = raw_row["storage_path"]

                # Idempotency check
                if not request.force:
                    existing = canonical_repo.find_existing(
                        source_asset_id=source_asset_id,
                        schema_version=CANONICAL_SCHEMA_VERSION,
                    )
                    if existing:
                        logger.info(
                            "Skipping %s — already normalized (schema %s)",
                            canonical_type, CANONICAL_SCHEMA_VERSION,
                        )
                        skipped.append(f"{canonical_type}:{source_asset_id}")
                        continue

                # Load raw
                logger.info("Loading raw %s from %s", canonical_type, storage_path)
                raw_df = load_raw_parquet(storage_path)

                # Canonicalize
                preserve = True  # from config
                if canonical_type == "laps":
                    canon_df, quality, dup_report = canonicalize_laps(
                        raw_df,
                        season=request.season,
                        event_name=request.event,
                        session_type=request.session_type,
                        preserve_unmapped=preserve,
                    )
                    out_path = output_dir / "laps.parquet"
                elif canonical_type == "telemetry":
                    driver = request.driver_code or raw_row.get("driver_code")
                    canon_df, quality, dup_report = canonicalize_telemetry(
                        raw_df,
                        season=request.season,
                        event_name=request.event,
                        session_type=request.session_type,
                        driver_code=driver,
                        preserve_unmapped=preserve,
                    )
                    telem_dir = output_dir / "telemetry"
                    telem_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{slug(driver)}.parquet" if driver else "all.parquet"
                    out_path = telem_dir / filename
                elif canonical_type == "weather":
                    canon_df, quality, dup_report = canonicalize_weather(
                        raw_df,
                        season=request.season,
                        event_name=request.event,
                        session_type=request.session_type,
                        preserve_unmapped=preserve,
                    )
                    out_path = output_dir / "weather.parquet"
                else:
                    skipped.append(f"unhandled:{canonical_type}")
                    continue

                quality_reports.append(quality)
                duplicate_reports.append(dup_report)

                # Save
                logger.info("Saving canonical %s → %s (%d rows)",
                            canonical_type, out_path, len(canon_df))
                out_path.parent.mkdir(parents=True, exist_ok=True)
                canon_df.to_parquet(out_path, index=False)
                checksum = file_sha256(out_path)
                rel_path = _clean_path(out_path)

                # Register in Supabase
                canonical_repo.create_asset(
                    normalization_run_id=norm_run_id,
                    source_asset_id=source_asset_id,
                    season=request.season,
                    event_name=request.event,
                    session_type=request.session_type,
                    driver_code=request.driver_code or raw_row.get("driver_code"),
                    asset_type=canonical_type,
                    storage_path=rel_path,
                    file_format="parquet",
                    checksum=checksum,
                    row_count=len(canon_df),
                    schema_version=CANONICAL_SCHEMA_VERSION,
                )

                assets.append(CanonicalAssetResult(
                    source_asset_id=source_asset_id,
                    asset_type=canonical_type,
                    season=request.season,
                    event=request.event,
                    session_type=request.session_type,
                    driver_code=request.driver_code or raw_row.get("driver_code"),
                    storage_path=rel_path,
                    checksum=checksum,
                    row_count=len(canon_df),
                    schema_version=CANONICAL_SCHEMA_VERSION,
                ))

            # Save metadata JSON
            metadata_path = output_dir / "metadata.json"
            metadata: dict[str, Any] = {
                "normalization_run_id": norm_run_id,
                "source_ingestion_run_id": source_run_id,
                "schema_version": CANONICAL_SCHEMA_VERSION,
                "season": request.season,
                "event": request.event,
                "session_type": request.session_type,
                "driver_code": request.driver_code,
                "assets": [a.model_dump(mode="json") for a in assets],
                "skipped": skipped,
            }
            with metadata_path.open("w", encoding="utf-8") as fh:
                json.dump(metadata, fh, indent=2, sort_keys=True)
                fh.write("\n")

            # Mark success
            norm_runs_repo.mark_success(norm_run_id)
            logger.info("Normalization run %s completed successfully.", norm_run_id)

            return Layer1NormalizationResult(
                normalization_run_id=norm_run_id,
                source_ingestion_run_id=source_run_id,
                assets=assets,
                skipped_assets=skipped,
                quality_reports=quality_reports,
                duplicate_reports=duplicate_reports,
                success=True,
                message="Layer 1 normalization completed successfully.",
            )

        except Exception as exc:
            logger.exception("Normalization failed: %s", exc)
            try:
                norm_runs_repo.mark_failed(norm_run_id, str(exc))
            except Exception:
                logger.error("Failed to mark normalization run as failed.")
            return Layer1NormalizationResult(
                normalization_run_id=norm_run_id,
                source_ingestion_run_id=source_run_id,
                assets=assets,
                skipped_assets=skipped,
                quality_reports=quality_reports,
                duplicate_reports=duplicate_reports,
                success=False,
                message=f"Normalization failed: {exc}",
            )


def run_layer1_normalization(
    request: Layer1NormalizationRequest,
) -> Layer1NormalizationResult:
    """Convenience entry-point."""
    return Layer1Pipeline().run(request)
