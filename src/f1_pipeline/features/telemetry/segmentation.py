"""Telemetry segmentation — braking events and straight-line detection.

All thresholds are configurable via ``configs/features.yaml``.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ======================================================================
# Braking events
# ======================================================================

def detect_braking_events(
    df: pd.DataFrame,
    min_speed_drop_kmh: float = 15.0,
    min_duration_s: float = 0.25,
    max_gap_s: float = 0.5,
) -> pd.DataFrame:
    """Detect braking events and compute per-event summary features.

    Parameters
    ----------
    df:
        Telemetry DataFrame that must contain ``brake_active``, ``speed``,
        ``distance``, ``dt``, and ``time`` columns.  Optionally
        ``acceleration_longitudinal`` for peak deceleration.
    min_speed_drop_kmh:
        Minimum speed loss (km/h) to qualify as a braking event.
    min_duration_s:
        Minimum braking duration (seconds).
    max_gap_s:
        Telemetry gaps larger than this within a braking zone disqualify
        the event.

    Returns
    -------
    pd.DataFrame
        One row per braking event with columns:
        braking_start_distance, braking_end_distance, braking_distance,
        braking_duration, entry_speed, minimum_speed, speed_loss,
        peak_deceleration.
    """
    required = {"brake_active", "speed", "distance", "dt", "time"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        logger.warning("Cannot detect braking events — missing: %s", sorted(missing))
        return pd.DataFrame()

    tmp = df.copy()

    # Ensure boolean brake state
    tmp["_brake_bool"] = tmp["brake_active"].astype(bool)

    # Assign a zone-id to each contiguous braking block.
    # Increment id each time we transition from not-braking to braking.
    tmp["_brake_start"] = tmp["_brake_bool"] & (~tmp["_brake_bool"].shift(1, fill_value=False))
    tmp["_zone_id"] = tmp["_brake_start"].cumsum()

    braking_rows = tmp[tmp["_brake_bool"]]
    if braking_rows.empty:
        return pd.DataFrame()

    events: list[dict] = []
    for _zone_id, group in braking_rows.groupby("_zone_id"):
        if len(group) < 2:
            continue

        # Duration from valid dt only
        valid_dt = group["dt"].dropna()
        if valid_dt.empty:
            continue
        duration = float(valid_dt.sum())
        if duration < min_duration_s:
            continue

        # Reject events that contain a telemetry gap
        if float(valid_dt.max()) > max_gap_s:
            continue

        entry_speed = float(group["speed"].iloc[0])
        min_speed = float(group["speed"].min())
        speed_loss = entry_speed - min_speed

        if speed_loss < min_speed_drop_kmh:
            continue

        start_dist = float(group["distance"].iloc[0])
        end_dist = float(group["distance"].iloc[-1])
        braking_dist = end_dist - start_dist
        if braking_dist < 0:
            continue

        # Peak deceleration (most negative longitudinal acceleration)
        if "acceleration_longitudinal" in group.columns:
            valid_accel = group["acceleration_longitudinal"].dropna()
            peak_dec = float(valid_accel.min()) if not valid_accel.empty else np.nan
        else:
            peak_dec = np.nan

        events.append({
            "braking_start_distance": start_dist,
            "braking_end_distance": end_dist,
            "braking_distance": braking_dist,
            "braking_duration": duration,
            "entry_speed": entry_speed,
            "minimum_speed": min_speed,
            "speed_loss": speed_loss,
            "peak_deceleration": peak_dec,
        })

    return pd.DataFrame(events)


# ======================================================================
# Straight-line detection
# ======================================================================

def detect_straight_lines(
    df: pd.DataFrame,
    throttle_threshold: float = 95.0,
    min_duration_s: float = 1.0,
) -> pd.DataFrame:
    """Detect straight-line regions via full-throttle heuristic.

    Parameters
    ----------
    df:
        Telemetry DataFrame with ``throttle_percent``, ``speed``,
        ``distance``, ``dt``.
    throttle_threshold:
        Throttle percentage at or above which is considered "full throttle".
    min_duration_s:
        Minimum straight duration in seconds.

    Returns
    -------
    pd.DataFrame
        One row per straight with columns:
        straight_start_distance, straight_end_distance, straight_length,
        time_at_full_throttle, maximum_speed, average_speed,
        DRS_active_fraction.
    """
    required = {"throttle_percent", "speed", "distance", "dt"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        logger.warning("Cannot detect straights — missing: %s", sorted(missing))
        return pd.DataFrame()

    tmp = df.copy()

    full_throttle = tmp["throttle_percent"] >= throttle_threshold
    # Zone id: increment each time we enter a full-throttle block
    entering = full_throttle & (~full_throttle.shift(1, fill_value=False))
    tmp["_straight_id"] = entering.cumsum()

    straight_rows = tmp[full_throttle]
    if straight_rows.empty:
        return pd.DataFrame()

    events: list[dict] = []
    for _sid, group in straight_rows.groupby("_straight_id"):
        valid_dt = group["dt"].dropna()
        duration = float(valid_dt.sum()) if not valid_dt.empty else 0.0
        if duration < min_duration_s:
            continue

        start_dist = float(group["distance"].iloc[0])
        end_dist = float(group["distance"].iloc[-1])
        length = end_dist - start_dist
        if length <= 0:
            continue

        max_speed = float(group["speed"].max())
        avg_speed = float(group["speed"].mean())

        drs_frac = 0.0
        if "drs_active" in group.columns:
            drs_frac = float(group["drs_active"].astype(float).mean())

        events.append({
            "straight_start_distance": start_dist,
            "straight_end_distance": end_dist,
            "straight_length": length,
            "time_at_full_throttle": duration,
            "maximum_speed": max_speed,
            "average_speed": avg_speed,
            "DRS_active_fraction": drs_frac,
        })

    return pd.DataFrame(events)
