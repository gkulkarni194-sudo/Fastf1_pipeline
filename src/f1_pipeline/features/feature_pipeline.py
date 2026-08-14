"""Layer 2 pipeline — derived physical feature extraction.

Workflow
--------
1.  Validate configuration.
2.  Test Supabase connectivity.
3.  Discover successful Layer 1 canonical assets.
4.  Create ``feature_run`` with status = started.
5.  For each canonical asset (per driver):
    a.  Check idempotency — skip if already processed with same
        (source_canonical_asset_id, feature_schema_version, config_hash).
    b.  Load canonical Parquet.
    c.  Calculate derived features:
        - telemetry derivatives → dynamics → controls → braking → straights
        - corners
        - lap features
        - stint features
        - session summary
    d.  Validate feature datasets.
    e.  Save feature Parquets under ``data/interim/features/``.
    f.  Calculate checksums.
    g.  Register ``feature_asset`` in Supabase.
6.  Save metadata JSON.
7.  Mark ``feature_run`` = success (or failed).
8.  Return ``Layer2FeatureResult``.
"""
from __future__ import annotations

import json
import logging
import os
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from f1_pipeline.core.hashing import file_sha256
from f1_pipeline.core.paths import PATHS, PROJECT_ROOT
from f1_pipeline.core.text import slug
from f1_pipeline.db.repositories.canonical_assets import CanonicalAssetsRepository
from f1_pipeline.db.repositories.feature_assets import FeatureAssetsRepository
from f1_pipeline.db.repositories.feature_runs import FeatureRunsRepository
from f1_pipeline.features.corners.corner_features import detect_corners
from f1_pipeline.features.laps.lap_features import compute_lap_features
from f1_pipeline.features.laps.stint_features import compute_stint_features
from f1_pipeline.features.schemas import (
    FEATURE_SCHEMA_VERSION,
    FeatureAssetResult,
    Layer2FeatureRequest,
    Layer2FeatureResult,
    QualityReport,
)
from f1_pipeline.features.telemetry.controls import compute_controls
from f1_pipeline.features.telemetry.derivatives import compute_derivatives
from f1_pipeline.features.telemetry.dynamics import compute_dynamics
from f1_pipeline.features.telemetry.segmentation import (
    detect_braking_events,
    detect_straight_lines,
)
from f1_pipeline.features.validation import validate_features

logger = logging.getLogger(__name__)


# ======================================================================
# Public API
# ======================================================================

class Layer2Pipeline:
    """Orchestrates Layer 2 feature extraction."""

    def __init__(
        self,
        *,
        canonical_assets: CanonicalAssetsRepository | None = None,
        feature_assets: FeatureAssetsRepository | None = None,
        feature_runs: FeatureRunsRepository | None = None,
        features_config: dict[str, Any] | None = None,
    ) -> None:
        self._canonical_assets_repo = canonical_assets
        self._feature_assets_repo = feature_assets
        self._feature_runs_repo = feature_runs
        self._features_config = features_config or {}

    # ------------------------------------------------------------------
    def run(self, request: Layer2FeatureRequest) -> Layer2FeatureResult:
        # ---------------------------------------------------------------
        # Phase 1 — Supabase connectivity
        # ---------------------------------------------------------------
        try:
            canon_repo = self._canonical_assets_repo or CanonicalAssetsRepository()
            feat_repo = self._feature_assets_repo or FeatureAssetsRepository()
            runs_repo = self._feature_runs_repo or FeatureRunsRepository()
            logger.info("Supabase host: %s", _supabase_hostname())
        except Exception as exc:
            logger.error("Supabase connection failed: %s", exc)
            return Layer2FeatureResult(
                success=False,
                message=f"Supabase connection failed: {exc}",
            )

        # ---------------------------------------------------------------
        # Phase 2 — Discover Layer 1 canonical assets
        # ---------------------------------------------------------------
        try:
            canonical_rows = _discover_canonical_assets(
                canon_repo,
                season=request.season,
                event=request.event,
                session_type=request.session_type,
                driver_code=request.driver_code,
            )
        except Exception as exc:
            logger.error("Canonical asset discovery failed: %s", exc)
            return Layer2FeatureResult(
                success=False,
                message=f"Canonical asset discovery failed: {exc}",
            )

        if not canonical_rows:
            return Layer2FeatureResult(
                success=False,
                message=(
                    f"No Layer 1 canonical assets found for "
                    f"{request.season}/{request.event}/{request.session_type}"
                    f"/{request.driver_code or 'all'}."
                ),
            )

        # Locate the normalization run id from the first canonical asset
        source_norm_run_id = canonical_rows[0].get("normalization_run_id")

        # ---------------------------------------------------------------
        # Phase 3 — Create feature_run
        # ---------------------------------------------------------------
        try:
            run_record = runs_repo.create_started(
                source_normalization_run_id=source_norm_run_id,
                config_hash=request.config_hash,
                code_version=request.code_version,
            )
            feature_run_id = str(run_record["id"])
            logger.info("Feature run created: %s", feature_run_id)
        except Exception as exc:
            logger.error("Failed to create feature_run: %s", exc)
            return Layer2FeatureResult(
                success=False,
                message=f"Failed to create feature_run: {exc}",
            )

        # ---------------------------------------------------------------
        # Phase 4 — Process canonical assets
        # ---------------------------------------------------------------
        assets: list[FeatureAssetResult] = []
        skipped: list[str] = []
        quality_reports: list[QualityReport] = []

        try:
            output_root = _feature_output_dir(
                request.season, request.event, request.session_type,
            )
            output_root.mkdir(parents=True, exist_ok=True)

            # Separate assets by type
            telem_assets = [r for r in canonical_rows if r.get("asset_type") == "telemetry"]
            laps_assets = [r for r in canonical_rows if r.get("asset_type") == "laps"]

            # Load laps (session-wide, not per-driver)
            laps_df: pd.DataFrame | None = None
            laps_asset_id: str | None = None
            for la in laps_assets:
                laps_path = _resolve_storage_path(la["storage_path"])
                if laps_path.exists():
                    laps_df = pd.read_parquet(laps_path)
                    laps_asset_id = str(la["id"])
                    logger.info("Loaded canonical laps: %d rows", len(laps_df))
                    break

            # ----------------------------------------------------------
            # Per-driver telemetry processing
            # ----------------------------------------------------------
            feature_sets = set(request.feature_sets)
            process_all = "all" in feature_sets

            for telem_row in telem_assets:
                source_asset_id = str(telem_row["id"])
                driver = telem_row.get("driver_code") or request.driver_code
                storage_path = telem_row["storage_path"]

                # Idempotency check
                if not request.force:
                    existing = feat_repo.find_existing(
                        source_canonical_asset_id=source_asset_id,
                        feature_schema_version=FEATURE_SCHEMA_VERSION,
                        config_hash=request.config_hash,
                    )
                    if existing:
                        logger.info(
                            "Skipping %s — already extracted (schema %s)",
                            driver, FEATURE_SCHEMA_VERSION,
                        )
                        skipped.append(f"telemetry:{source_asset_id}")
                        continue

                # Load canonical telemetry
                telem_path = _resolve_storage_path(storage_path)
                if not telem_path.exists():
                    logger.warning("Canonical telemetry not found: %s", telem_path)
                    skipped.append(f"missing:{storage_path}")
                    continue

                telem_df = pd.read_parquet(telem_path)
                logger.info(
                    "Processing driver=%s, %d telemetry rows",
                    driver, len(telem_df),
                )

                # Read config thresholds
                telem_cfg = self._features_config.get("telemetry", {})
                deriv_cfg = telem_cfg.get("derivatives", {})
                braking_cfg = telem_cfg.get("braking", {})
                straight_cfg = telem_cfg.get("straight_line", {})
                corner_cfg = self._features_config.get("corners", {})

                max_gap = deriv_cfg.get("max_gap_seconds", 0.5)

                # ---- Telemetry features ----
                if process_all or "telemetry" in feature_sets:
                    derived = compute_derivatives(telem_df, max_gap_seconds=max_gap)
                    derived = compute_dynamics(derived, max_gap_seconds=max_gap)
                    derived = compute_controls(derived)

                    derived, telem_qr = validate_features(derived, "telemetry")
                    quality_reports.append(telem_qr)

                    # Save telemetry features
                    telem_out_dir = output_root / "telemetry"
                    telem_out_dir.mkdir(parents=True, exist_ok=True)
                    telem_out_path = telem_out_dir / f"{slug(driver or 'unknown')}.parquet"
                    derived.to_parquet(telem_out_path, index=False)
                    checksum = file_sha256(telem_out_path)

                    feat_repo.create_asset(
                        feature_run_id=feature_run_id,
                        source_canonical_asset_id=source_asset_id,
                        season=request.season,
                        event_name=request.event,
                        session_type=request.session_type,
                        driver_code=driver,
                        asset_type="derived_telemetry",
                        storage_path=_clean_path(telem_out_path),
                        file_format="parquet",
                        checksum=checksum,
                        row_count=len(derived),
                        feature_schema_version=FEATURE_SCHEMA_VERSION,
                        config_hash=request.config_hash,
                    )
                    assets.append(FeatureAssetResult(
                        source_asset_id=source_asset_id,
                        asset_type="derived_telemetry",
                        season=request.season,
                        event=request.event,
                        session_type=request.session_type,
                        driver_code=driver,
                        storage_path=_clean_path(telem_out_path),
                        checksum=checksum,
                        row_count=len(derived),
                    ))
                else:
                    # Need at least derivatives for other features
                    derived = compute_derivatives(telem_df, max_gap_seconds=max_gap)
                    derived = compute_dynamics(derived, max_gap_seconds=max_gap)
                    derived = compute_controls(derived)

                # ---- Braking / Straight segmentation (stored in stints dir) ----
                braking_df = detect_braking_events(
                    derived,
                    min_speed_drop_kmh=braking_cfg.get("minimum_speed_drop_kmh", 15.0),
                    min_duration_s=braking_cfg.get("minimum_duration_s", 0.25),
                    max_gap_s=braking_cfg.get("maximum_gap_s", 0.5),
                )
                straights_df = detect_straight_lines(
                    derived,
                    throttle_threshold=straight_cfg.get("throttle_threshold", 95.0),
                    min_duration_s=straight_cfg.get("minimum_duration_s", 1.0),
                )

                # ---- Corners ----
                corners_df = pd.DataFrame()
                if process_all or "corners" in feature_sets:
                    corners_df = detect_corners(
                        derived,
                        min_speed_drop_kmh=corner_cfg.get("minimum_speed_drop_for_corner_kmh", 30.0),
                        min_corner_duration_s=corner_cfg.get("minimum_corner_duration_s", 0.5),
                        max_distance_to_min_speed_m=corner_cfg.get(
                            "maximum_distance_between_braking_and_min_speed_m", 200.0
                        ),
                    )
                    if not corners_df.empty:
                        corners_df, corner_qr = validate_features(corners_df, "corners")
                        quality_reports.append(corner_qr)

                        corners_dir = output_root / "corners"
                        corners_dir.mkdir(parents=True, exist_ok=True)
                        corners_path = corners_dir / f"{slug(driver or 'unknown')}.parquet"
                        corners_df.to_parquet(corners_path, index=False)
                        cksum = file_sha256(corners_path)

                        feat_repo.create_asset(
                            feature_run_id=feature_run_id,
                            source_canonical_asset_id=source_asset_id,
                            season=request.season,
                            event_name=request.event,
                            session_type=request.session_type,
                            driver_code=driver,
                            asset_type="corners",
                            storage_path=_clean_path(corners_path),
                            file_format="parquet",
                            checksum=cksum,
                            row_count=len(corners_df),
                            feature_schema_version=FEATURE_SCHEMA_VERSION,
                            config_hash=request.config_hash,
                        )
                        assets.append(FeatureAssetResult(
                            source_asset_id=source_asset_id,
                            asset_type="corners",
                            season=request.season,
                            event=request.event,
                            session_type=request.session_type,
                            driver_code=driver,
                            storage_path=_clean_path(corners_path),
                            checksum=cksum,
                            row_count=len(corners_df),
                        ))

                # ---- Lap features (per driver) ----
                if (process_all or "laps" in feature_sets) and laps_df is not None:
                    driver_laps = laps_df
                    if driver and "driver_code" in laps_df.columns:
                        driver_laps = laps_df[laps_df["driver_code"] == driver].copy()

                    if not driver_laps.empty:
                        lap_feat = compute_lap_features(
                            driver_laps,
                            telemetry_df=derived,
                            braking_events_df=braking_df,
                            corners_df=corners_df,
                        )
                        lap_feat, lap_qr = validate_features(lap_feat, "laps")
                        quality_reports.append(lap_qr)

                        laps_dir = output_root / "laps"
                        laps_dir.mkdir(parents=True, exist_ok=True)
                        laps_path = laps_dir / f"{slug(driver or 'unknown')}.parquet"
                        lap_feat.to_parquet(laps_path, index=False)
                        cksum = file_sha256(laps_path)

                        feat_repo.create_asset(
                            feature_run_id=feature_run_id,
                            source_canonical_asset_id=laps_asset_id or source_asset_id,
                            season=request.season,
                            event_name=request.event,
                            session_type=request.session_type,
                            driver_code=driver,
                            asset_type="derived_laps",
                            storage_path=_clean_path(laps_path),
                            file_format="parquet",
                            checksum=cksum,
                            row_count=len(lap_feat),
                            feature_schema_version=FEATURE_SCHEMA_VERSION,
                            config_hash=request.config_hash,
                        )
                        assets.append(FeatureAssetResult(
                            source_asset_id=laps_asset_id or source_asset_id,
                            asset_type="derived_laps",
                            season=request.season,
                            event=request.event,
                            session_type=request.session_type,
                            driver_code=driver,
                            storage_path=_clean_path(laps_path),
                            checksum=cksum,
                            row_count=len(lap_feat),
                        ))

                # ---- Stint features (per driver) ----
                if (process_all or "stints" in feature_sets) and laps_df is not None:
                    driver_laps = laps_df
                    if driver and "driver_code" in laps_df.columns:
                        driver_laps = laps_df[laps_df["driver_code"] == driver].copy()

                    if not driver_laps.empty:
                        stint_feat = compute_stint_features(
                            driver_laps, telemetry_df=derived,
                        )
                        if not stint_feat.empty:
                            stint_feat, stint_qr = validate_features(stint_feat, "stints")
                            quality_reports.append(stint_qr)

                            stints_dir = output_root / "stints"
                            stints_dir.mkdir(parents=True, exist_ok=True)
                            stints_path = stints_dir / f"{slug(driver or 'unknown')}.parquet"
                            stint_feat.to_parquet(stints_path, index=False)
                            cksum = file_sha256(stints_path)

                            feat_repo.create_asset(
                                feature_run_id=feature_run_id,
                                source_canonical_asset_id=laps_asset_id or source_asset_id,
                                season=request.season,
                                event_name=request.event,
                                session_type=request.session_type,
                                driver_code=driver,
                                asset_type="stints",
                                storage_path=_clean_path(stints_path),
                                file_format="parquet",
                                checksum=cksum,
                                row_count=len(stint_feat),
                                feature_schema_version=FEATURE_SCHEMA_VERSION,
                                config_hash=request.config_hash,
                            )
                            assets.append(FeatureAssetResult(
                                source_asset_id=laps_asset_id or source_asset_id,
                                asset_type="stints",
                                season=request.season,
                                event=request.event,
                                session_type=request.session_type,
                                driver_code=driver,
                                storage_path=_clean_path(stints_path),
                                checksum=cksum,
                                row_count=len(stint_feat),
                            ))

            # ----------------------------------------------------------
            # Session summary
            # ----------------------------------------------------------
            summary_df = _build_session_summary(laps_df, canonical_rows)
            if summary_df is not None and not summary_df.empty:
                summary_df, sum_qr = validate_features(summary_df, "session_summary")
                quality_reports.append(sum_qr)
                summary_path = output_root / "session_summary.parquet"
                summary_df.to_parquet(summary_path, index=False)

            # ----------------------------------------------------------
            # Metadata JSON
            # ----------------------------------------------------------
            metadata: dict[str, Any] = {
                "feature_run_id": feature_run_id,
                "source_normalization_run_id": source_norm_run_id,
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "season": request.season,
                "event": request.event,
                "session_type": request.session_type,
                "driver_code": request.driver_code,
                "assets": [a.model_dump(mode="json") for a in assets],
                "skipped": skipped,
                "quality_reports": [qr.model_dump(mode="json") for qr in quality_reports],
            }
            metadata_path = output_root / "metadata.json"
            with metadata_path.open("w", encoding="utf-8") as fh:
                json.dump(metadata, fh, indent=2, sort_keys=True, default=str)
                fh.write("\n")

            # Mark success
            runs_repo.mark_success(feature_run_id)
            logger.info("Feature run %s completed successfully.", feature_run_id)

            return Layer2FeatureResult(
                feature_run_id=feature_run_id,
                source_normalization_run_id=source_norm_run_id,
                assets=assets,
                skipped_assets=skipped,
                quality_reports=quality_reports,
                success=True,
                message="Layer 2 feature extraction completed successfully.",
            )

        except Exception as exc:
            logger.exception("Feature extraction failed: %s", exc)
            try:
                runs_repo.mark_failed(feature_run_id, str(exc))
            except Exception:
                logger.error("Failed to mark feature_run as failed.")
            return Layer2FeatureResult(
                feature_run_id=feature_run_id,
                source_normalization_run_id=source_norm_run_id,
                assets=assets,
                skipped_assets=skipped,
                quality_reports=quality_reports,
                success=False,
                message=f"Feature extraction failed: {exc}",
            )


def run_layer2_features(
    request: Layer2FeatureRequest,
    features_config: dict[str, Any] | None = None,
) -> Layer2FeatureResult:
    """Convenience entry-point."""
    return Layer2Pipeline(features_config=features_config).run(request)


# ======================================================================
# Helpers
# ======================================================================

def _supabase_hostname() -> str:
    url = os.getenv("SUPABASE_URL", "")
    try:
        return urlparse(url).hostname or "<not set>"
    except Exception:
        return "<invalid url>"


def _feature_output_dir(season: int, event: str, session_type: str) -> Path:
    return (
        PATHS.interim / "features"
        / str(season) / slug(event) / slug(session_type)
    )


def _resolve_storage_path(storage_path: str) -> Path:
    """Resolve a relative storage path to an absolute path."""
    p = Path(storage_path)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p


def _clean_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _discover_canonical_assets(
    repo: CanonicalAssetsRepository,
    *,
    season: int,
    event: str,
    session_type: str,
    driver_code: str | None,
) -> list[dict[str, Any]]:
    """Query Supabase for canonical assets matching the request."""
    query = (
        repo.client.table(repo.table_name)
        .select("*")
        .eq("season", season)
        .eq("event_name", event)
        .eq("session_type", session_type)
    )
    if driver_code:
        query = query.eq("driver_code", driver_code)

    return query.order("created_at", desc=True).execute().data


def _build_session_summary(
    laps_df: pd.DataFrame | None,
    canonical_rows: list[dict[str, Any]],
) -> pd.DataFrame | None:
    """Build a session-level summary DataFrame (one row per driver)."""
    if laps_df is None or laps_df.empty:
        return None
    if "driver_code" not in laps_df.columns:
        return None

    rows: list[dict] = []
    for driver, group in laps_df.groupby("driver_code"):
        valid = group.dropna(subset=["lap_time"]) if "lap_time" in group.columns else group

        # Lap times in seconds
        if "lap_time" in valid.columns:
            lt = valid["lap_time"]
            if pd.api.types.is_timedelta64_dtype(lt):
                lt_s = lt.dt.total_seconds()
            else:
                lt_s = pd.to_numeric(lt, errors="coerce")
        else:
            lt_s = pd.Series(dtype=float)

        lt_s = lt_s.dropna()

        rows.append({
            "driver": driver,
            "best_lap": float(lt_s.min()) if not lt_s.empty else np.nan,
            "median_lap": float(lt_s.median()) if not lt_s.empty else np.nan,
            "mean_lap": float(lt_s.mean()) if not lt_s.empty else np.nan,
            "total_laps": len(group),
            "valid_laps": len(valid),
            "total_stints": int(group["stint"].nunique()) if "stint" in group.columns else np.nan,
        })

    return pd.DataFrame(rows) if rows else None
