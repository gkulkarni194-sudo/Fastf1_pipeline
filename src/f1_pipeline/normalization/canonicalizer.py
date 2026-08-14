"""Canonicalizer — coordinates the full normalization pipeline per asset type.

    load raw parquet
        → apply column mapping
        → normalize types
        → normalize units
        → normalize missing values
        → detect/flag duplicates
        → validate
        → return (canonical_df, quality_report, duplicate_report)

This module is **deterministic** and contains **no database logic**.
Running it twice on the same input must produce the same output.
"""
from __future__ import annotations

import pandas as pd

from f1_pipeline.normalization.column_mapping import (
    LAPS_COLUMN_MAP,
    TELEMETRY_COLUMN_MAP,
    WEATHER_COLUMN_MAP,
    apply_column_mapping,
)
from f1_pipeline.normalization.missing_values import normalize_missing_values
from f1_pipeline.normalization.schemas import DuplicateReport, QualityReport
from f1_pipeline.normalization.type_normalization import (
    normalize_lap_types,
    normalize_telemetry_types,
    normalize_weather_types,
)
from f1_pipeline.normalization.unit_normalization import apply_unit_normalization
from f1_pipeline.normalization.validation import (
    validate_laps,
    validate_telemetry,
    validate_weather,
)


# ---------------------------------------------------------------------------
# Duplicate detection helpers
# ---------------------------------------------------------------------------
_LAPS_IDENTITY = ["driver_code", "lap_number"]
_TELEM_IDENTITY = ["driver_code", "lap_number", "time"]
_WEATHER_IDENTITY = ["time"]


def _detect_duplicates(
    df: pd.DataFrame,
    identity_cols: list[str],
    asset_type: str,
) -> tuple[pd.DataFrame, DuplicateReport]:
    """Remove exact duplicate rows based on *identity_cols*.

    Only columns that actually exist in *df* are used.
    """
    usable = [c for c in identity_cols if c in df.columns]
    rows_before = len(df)

    if usable:
        out = df.drop_duplicates(subset=usable, keep="first")
    else:
        out = df.drop_duplicates(keep="first")

    rows_after = len(out)
    return out, DuplicateReport(
        asset_type=asset_type,
        rows_before=rows_before,
        duplicates_found=rows_before - rows_after,
        rows_after=rows_after,
    )


# ---------------------------------------------------------------------------
# Public canonicalization functions
# ---------------------------------------------------------------------------
def canonicalize_laps(
    df: pd.DataFrame,
    *,
    season: int,
    event_name: str,
    session_type: str,
    preserve_unmapped: bool = True,
) -> tuple[pd.DataFrame, QualityReport, DuplicateReport]:
    """Canonicalize a raw laps DataFrame."""
    context = {"season": season, "event_name": event_name, "session_type": session_type}

    out = apply_column_mapping(df, LAPS_COLUMN_MAP, preserve_unmapped=preserve_unmapped, context=context)
    out = normalize_lap_types(out)
    out = apply_unit_normalization(out, "laps")
    out = normalize_missing_values(out)
    out, dup_report = _detect_duplicates(out, _LAPS_IDENTITY, "laps")
    quality = validate_laps(out)

    return out, quality, dup_report


def canonicalize_telemetry(
    df: pd.DataFrame,
    *,
    season: int,
    event_name: str,
    session_type: str,
    driver_code: str | None = None,
    preserve_unmapped: bool = True,
) -> tuple[pd.DataFrame, QualityReport, DuplicateReport]:
    """Canonicalize a raw telemetry DataFrame."""
    context = {"season": season, "event_name": event_name, "session_type": session_type}
    if driver_code:
        context["driver_code"] = driver_code

    out = apply_column_mapping(df, TELEMETRY_COLUMN_MAP, preserve_unmapped=preserve_unmapped, context=context)
    out = normalize_telemetry_types(out)
    out = apply_unit_normalization(out, "telemetry")
    out = normalize_missing_values(out)
    out, dup_report = _detect_duplicates(out, _TELEM_IDENTITY, "telemetry")
    quality = validate_telemetry(out)

    return out, quality, dup_report


def canonicalize_weather(
    df: pd.DataFrame,
    *,
    season: int,
    event_name: str,
    session_type: str,
    preserve_unmapped: bool = True,
) -> tuple[pd.DataFrame, QualityReport, DuplicateReport]:
    """Canonicalize a raw weather DataFrame."""
    context = {"season": season, "event_name": event_name, "session_type": session_type}

    out = apply_column_mapping(df, WEATHER_COLUMN_MAP, preserve_unmapped=preserve_unmapped, context=context)
    out = normalize_weather_types(out)
    out = apply_unit_normalization(out, "weather")
    out = normalize_missing_values(out)
    out, dup_report = _detect_duplicates(out, _WEATHER_IDENTITY, "weather")
    quality = validate_weather(out)

    return out, quality, dup_report
