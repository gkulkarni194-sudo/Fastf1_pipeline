"""Per-lap derived features.

Enriches the canonical laps DataFrame with per-lap statistics derived
from telemetry.  All original canonical values (``lap_time``, sector
times, etc.) are **preserved** — this module only adds new columns.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_lap_features(
    laps_df: pd.DataFrame,
    telemetry_df: pd.DataFrame | None = None,
    braking_events_df: pd.DataFrame | None = None,
    corners_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute per-lap features.

    Parameters
    ----------
    laps_df:
        Canonical laps DataFrame (one row per lap).
    telemetry_df:
        Derived telemetry (after derivatives + controls).  If ``None``
        or empty, telemetry-derived columns will be NaN.
    braking_events_df:
        Output of ``detect_braking_events`` (one row per event).
        Used only for the ``number_of_braking_events`` count.
    corners_df:
        Output of ``detect_corners`` (one row per corner).
        Used only for the ``number_of_detected_corners`` count.

    Returns
    -------
    pd.DataFrame
        Copy of *laps_df* with added feature columns.
    """
    out = laps_df.copy()

    # ------------------------------------------------------------------
    # lap_time_seconds — numeric seconds from the canonical timedelta
    # ------------------------------------------------------------------
    if "lap_time" in out.columns:
        out["lap_time_seconds"] = _to_seconds(out["lap_time"])
    else:
        out["lap_time_seconds"] = np.nan

    # Sector times to seconds
    for sector in ("sector1_time", "sector2_time", "sector3_time"):
        sec_col = f"{sector}_seconds"
        if sector in out.columns:
            out[sec_col] = _to_seconds(out[sector])

    # ------------------------------------------------------------------
    # Telemetry-derived per-lap aggregates
    # ------------------------------------------------------------------
    telem_stats = _aggregate_telemetry_per_lap(telemetry_df)
    if telem_stats is not None:
        merge_cols = []
        if "driver_code" in out.columns and "driver_code" in telem_stats.columns:
            merge_cols.append("driver_code")
        if "lap_number" in out.columns and "lap_number" in telem_stats.columns:
            merge_cols.append("lap_number")
        if merge_cols:
            out = out.merge(telem_stats, on=merge_cols, how="left", suffixes=("", "_telem"))

    # ------------------------------------------------------------------
    # Braking event count
    # ------------------------------------------------------------------
    if braking_events_df is not None and not braking_events_df.empty:
        out["number_of_braking_events"] = len(braking_events_df)
    else:
        out["number_of_braking_events"] = np.nan

    # ------------------------------------------------------------------
    # Corner count
    # ------------------------------------------------------------------
    if corners_df is not None and not corners_df.empty:
        out["number_of_detected_corners"] = len(corners_df)
    else:
        out["number_of_detected_corners"] = np.nan

    return out


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _aggregate_telemetry_per_lap(
    telem: pd.DataFrame | None,
) -> pd.DataFrame | None:
    """Group telemetry by driver + lap and compute per-lap stats."""
    if telem is None or telem.empty:
        return None

    group_cols = []
    if "driver_code" in telem.columns:
        group_cols.append("driver_code")
    if "lap_number" in telem.columns:
        group_cols.append("lap_number")
    if not group_cols:
        return None

    rows: list[dict] = []
    for keys, group in telem.groupby(group_cols):
        if not isinstance(keys, tuple):
            keys = (keys,)
        rec: dict = dict(zip(group_cols, keys))

        rec["average_speed"] = _safe_stat(group, "speed", "mean")
        rec["maximum_speed"] = _safe_stat(group, "speed", "max")
        rec["maximum_acceleration"] = _safe_stat(group, "acceleration_longitudinal", "max")
        rec["maximum_deceleration"] = _safe_stat(group, "acceleration_longitudinal", "min")

        if "throttle_percent" in group.columns:
            tp = group["throttle_percent"].dropna()
            rec["throttle_fraction"] = float(tp.mean()) / 100.0 if not tp.empty else np.nan
        else:
            rec["throttle_fraction"] = np.nan

        rec["brake_fraction"] = _safe_stat(group, "brake_active", "mean")
        rec["DRS_fraction"] = _safe_stat(group, "drs_active", "mean")

        rows.append(rec)

    return pd.DataFrame(rows) if rows else None


def _safe_stat(group: pd.DataFrame, col: str, stat: str) -> float:
    if col not in group.columns:
        return np.nan
    s = group[col].dropna()
    if s.empty:
        return np.nan
    if stat == "max":
        return float(s.max())
    if stat == "min":
        return float(s.min())
    if stat == "mean":
        return float(s.mean())
    return np.nan


def _to_seconds(series: pd.Series) -> pd.Series:
    """Convert a timedelta / numeric column to float seconds."""
    if pd.api.types.is_timedelta64_dtype(series):
        return series.dt.total_seconds()
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    try:
        return pd.to_timedelta(series, errors="coerce").dt.total_seconds()
    except Exception:
        return pd.to_numeric(series, errors="coerce")
