"""Telemetry time-series derivatives.

Computes dt, distance_delta, speed_delta, acceleration_longitudinal,
and jerk from canonical telemetry.  All calculations use actual time
differences (not blind ``diff()``) and respect a configurable
maximum-gap threshold.

Canonical Layer 1 speed is in **km/h** (``speed`` column).
Physics calculations use m/s internally; both are preserved:
    speed       — original canonical km/h (never overwritten)
    speed_ms    — converted m/s (added column)
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

KMH_TO_MS = 1.0 / 3.6


def compute_derivatives(
    df: pd.DataFrame,
    max_gap_seconds: float = 0.5,
) -> pd.DataFrame:
    """Compute kinematic derivatives from canonical telemetry.

    Parameters
    ----------
    df:
        Canonical telemetry with at minimum a ``time`` column
        (timedelta64 or numeric seconds) and a ``speed`` column (km/h).
    max_gap_seconds:
        Any time gap larger than this is treated as invalid; derived
        values across the gap are set to NaN.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with added columns: ``dt``, ``speed_ms``,
        ``speed_delta``, ``distance_delta``, ``acceleration_longitudinal``,
        ``jerk``.
    """
    if df.empty:
        logger.warning("compute_derivatives received an empty DataFrame.")
        return _empty_with_columns(df)

    out = df.copy()

    # ------------------------------------------------------------------
    # 1. Time delta (seconds)
    # ------------------------------------------------------------------
    time_seconds = _time_to_seconds(out["time"])
    out["dt"] = time_seconds.diff()

    # Mask: invalid dt (NaN, zero, negative, exceeds gap)
    invalid_dt = out["dt"].isna() | (out["dt"] <= 0) | (out["dt"] > max_gap_seconds)

    # ------------------------------------------------------------------
    # 2. Speed in m/s (preserve original km/h)
    # ------------------------------------------------------------------
    if "speed" in out.columns:
        out["speed_ms"] = out["speed"] * KMH_TO_MS
    else:
        logger.warning("No 'speed' column — derivative calculations will be partial.")
        out["speed_ms"] = np.nan

    # ------------------------------------------------------------------
    # 3. Speed delta (m/s)
    # ------------------------------------------------------------------
    out["speed_delta"] = out["speed_ms"].diff()
    out.loc[invalid_dt, "speed_delta"] = np.nan

    # ------------------------------------------------------------------
    # 4. Distance delta
    # ------------------------------------------------------------------
    if "distance" in out.columns:
        out["distance_delta"] = out["distance"].diff()
        out.loc[invalid_dt, "distance_delta"] = np.nan
    else:
        out["distance_delta"] = np.nan

    # ------------------------------------------------------------------
    # 5. Longitudinal acceleration  a = dv / dt  (m/s²)
    # ------------------------------------------------------------------
    out["acceleration_longitudinal"] = np.where(
        invalid_dt,
        np.nan,
        out["speed_delta"] / out["dt"],
    )

    # ------------------------------------------------------------------
    # 6. Jerk  j = da / dt  (m/s³)
    # ------------------------------------------------------------------
    accel_delta = pd.Series(out["acceleration_longitudinal"], dtype=float).diff()
    # Jerk is invalid when *either* the current *or* the previous dt is
    # invalid, because we need two consecutive valid accelerations.
    prev_invalid = invalid_dt.shift(1, fill_value=True)
    jerk_invalid = invalid_dt | prev_invalid

    out["jerk"] = np.where(
        jerk_invalid,
        np.nan,
        accel_delta / out["dt"],
    )

    # ------------------------------------------------------------------
    # 7. Scrub any remaining inf / -inf
    # ------------------------------------------------------------------
    _replace_inf(out)

    return out


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _time_to_seconds(series: pd.Series) -> pd.Series:
    """Convert a time column to float seconds.

    Handles:
    * ``timedelta64`` / ``Timedelta``
    * Already-numeric (assumed seconds)
    * ``NaT`` → NaN
    """
    if pd.api.types.is_timedelta64_dtype(series):
        return series.dt.total_seconds()
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    # Attempt coercion
    try:
        return pd.to_timedelta(series, errors="coerce").dt.total_seconds()
    except Exception:
        logger.error("Cannot convert 'time' column to seconds; filling with NaN.")
        return pd.Series(np.nan, index=series.index)


def _replace_inf(df: pd.DataFrame) -> None:
    """Replace ±inf with NaN in all numeric columns, **in-place**."""
    numeric = df.select_dtypes(include=[np.number]).columns
    for col in numeric:
        mask = np.isinf(df[col])
        if mask.any():
            df.loc[mask, col] = np.nan


def _empty_with_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with the expected derivative columns added (all empty)."""
    out = df.copy()
    for col in ("dt", "speed_ms", "speed_delta", "distance_delta",
                "acceleration_longitudinal", "jerk"):
        if col not in out.columns:
            out[col] = pd.Series(dtype=float)
    return out
