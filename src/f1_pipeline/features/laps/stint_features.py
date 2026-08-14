"""Per-stint descriptive features.

Computes aggregate statistics for each driver × stint combination.
Does NOT fit a tyre-degradation model — that belongs to a later layer.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_stint_features(
    laps_df: pd.DataFrame,
    telemetry_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute descriptive features for each stint.

    Parameters
    ----------
    laps_df:
        Canonical laps DataFrame with at least ``driver_code``,
        ``stint``, ``lap_time``, ``compound``, ``lap_number``.
    telemetry_df:
        Optional derived telemetry for per-stint ``mean_speed``.

    Returns
    -------
    pd.DataFrame
        One row per (driver, stint) with descriptive stats.
    """
    required = {"driver_code", "stint", "lap_time", "lap_number"}
    if not required.issubset(laps_df.columns):
        missing = required - set(laps_df.columns)
        logger.warning("Cannot compute stint features — missing: %s", sorted(missing))
        return pd.DataFrame()

    rows: list[dict] = []

    for (driver, stint), group in laps_df.groupby(["driver_code", "stint"]):
        if len(group) == 0:
            continue

        valid_laps = group.dropna(subset=["lap_time"])

        compound = group["compound"].iloc[0] if "compound" in group.columns else None
        start_lap = int(group["lap_number"].min())
        end_lap = int(group["lap_number"].max())
        stint_length = end_lap - start_lap + 1

        # Lap times in seconds
        lap_times_s = _to_seconds(valid_laps["lap_time"]) if not valid_laps.empty else pd.Series(dtype=float)
        lap_times_s = lap_times_s.dropna()

        mean_lt = float(lap_times_s.mean()) if not lap_times_s.empty else None
        best_lt = float(lap_times_s.min()) if not lap_times_s.empty else None
        median_lt = float(lap_times_s.median()) if not lap_times_s.empty else None
        std_lt = float(lap_times_s.std(ddof=0)) if len(lap_times_s) > 1 else None

        # Tyre life
        tyre_life_start = None
        tyre_life_end = None
        if "tyre_life" in group.columns:
            tl = group["tyre_life"].dropna()
            if not tl.empty:
                tyre_life_start = float(tl.min())
                tyre_life_end = float(tl.max())

        # Mean speed from telemetry
        mean_speed = _compute_stint_mean_speed(
            telemetry_df, driver, group["lap_number"]
        )

        rows.append({
            "driver_code": driver,
            "stint_number": stint,
            "compound": compound,
            "starting_lap": start_lap,
            "ending_lap": end_lap,
            "stint_length": stint_length,
            "mean_lap_time": mean_lt,
            "best_lap_time": best_lt,
            "median_lap_time": median_lt,
            "lap_time_std": std_lt,
            "mean_speed": mean_speed,
            "tyre_life_start": tyre_life_start,
            "tyre_life_end": tyre_life_end,
        })

    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _to_seconds(series: pd.Series) -> pd.Series:
    """Convert a timedelta or numeric series to float seconds."""
    if pd.api.types.is_timedelta64_dtype(series):
        return series.dt.total_seconds()
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    try:
        return pd.to_timedelta(series, errors="coerce").dt.total_seconds()
    except Exception:
        return pd.to_numeric(series, errors="coerce")


def _compute_stint_mean_speed(
    telem: pd.DataFrame | None,
    driver: str,
    lap_numbers: pd.Series,
) -> float | None:
    """Return mean speed for a driver's stint laps from telemetry."""
    if telem is None or telem.empty:
        return None
    if "speed" not in telem.columns:
        return None
    if "driver_code" not in telem.columns or "lap_number" not in telem.columns:
        return None

    mask = (telem["driver_code"] == driver) & (telem["lap_number"].isin(lap_numbers))
    subset = telem.loc[mask, "speed"].dropna()
    if subset.empty:
        return None
    return float(subset.mean())
