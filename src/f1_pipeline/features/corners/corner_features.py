"""Corner detection via speed-profile heuristic.

This module identifies corner-like regions using the speed trace.  A
"corner" is defined as a contiguous region where speed drops below a
local threshold, flanked by higher-speed zones.

.. important::

   Corner IDs produced here are **sequential heuristic indices** — they
   do NOT correspond to official FIA corner numbers.

   ``corner_detection_method = "speed_profile_heuristic"``

All thresholds are read from ``configs/features.yaml`` → ``features.corners``.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def detect_corners(
    df: pd.DataFrame,
    *,
    min_speed_drop_kmh: float = 30.0,
    min_corner_duration_s: float = 0.5,
    max_distance_to_min_speed_m: float = 200.0,
) -> pd.DataFrame:
    """Detect corner-like regions from telemetry speed profile.

    Parameters
    ----------
    df:
        Telemetry with ``speed`` (km/h), ``distance`` (m), ``dt`` (s).
        Optionally ``acceleration_longitudinal`` for exit-accel.
    min_speed_drop_kmh:
        Minimum drop from the preceding local-max speed to qualify.
    min_corner_duration_s:
        Minimum time spent in the deceleration–acceleration region.
    max_distance_to_min_speed_m:
        Maximum distance between braking start and minimum speed point.

    Returns
    -------
    pd.DataFrame
        One row per detected corner with columns:
        corner_index, corner_detection_method, corner_entry_speed,
        minimum_corner_speed, corner_exit_speed,
        entry_to_min_speed_loss, exit_acceleration,
        corner_duration, approximate_corner_distance.
    """
    required = {"speed", "distance", "dt"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        logger.warning("Cannot detect corners — missing: %s", sorted(missing))
        return pd.DataFrame()

    if len(df) < 3:
        return pd.DataFrame()

    speed = df["speed"].to_numpy(dtype=float, na_value=np.nan)
    distance = df["distance"].to_numpy(dtype=float, na_value=np.nan)
    dt = df["dt"].to_numpy(dtype=float, na_value=np.nan) if "dt" in df.columns else None

    # ------------------------------------------------------------------
    # Find local minima in the speed trace.
    # A local minimum is where speed[i] <= speed[i-1] and speed[i] <= speed[i+1].
    # ------------------------------------------------------------------
    local_min_mask = np.zeros(len(speed), dtype=bool)
    for i in range(1, len(speed) - 1):
        if np.isnan(speed[i]):
            continue
        prev_ok = not np.isnan(speed[i - 1])
        next_ok = not np.isnan(speed[i + 1])
        if prev_ok and next_ok and speed[i] <= speed[i - 1] and speed[i] <= speed[i + 1]:
            local_min_mask[i] = True

    min_indices = np.where(local_min_mask)[0]
    if len(min_indices) == 0:
        return pd.DataFrame()

    corners: list[dict] = []
    corner_idx = 0

    for mi in min_indices:
        min_speed = speed[mi]
        if np.isnan(min_speed):
            continue

        # Walk backward to find entry (local max before this min)
        entry_idx = mi
        for j in range(mi - 1, -1, -1):
            if np.isnan(speed[j]):
                break
            if speed[j] >= speed[entry_idx]:
                entry_idx = j
            else:
                break

        # Walk forward to find exit (local max after this min)
        exit_idx = mi
        for j in range(mi + 1, len(speed)):
            if np.isnan(speed[j]):
                break
            if speed[j] >= speed[exit_idx]:
                exit_idx = j
            else:
                break

        entry_speed = speed[entry_idx]
        exit_speed = speed[exit_idx]
        speed_drop = entry_speed - min_speed

        if speed_drop < min_speed_drop_kmh:
            continue

        # Distance constraint
        if not np.isnan(distance[entry_idx]) and not np.isnan(distance[mi]):
            dist_to_min = distance[mi] - distance[entry_idx]
            if dist_to_min > max_distance_to_min_speed_m or dist_to_min < 0:
                continue
        else:
            dist_to_min = np.nan

        # Duration constraint
        if dt is not None:
            # Sum dt from entry to exit
            dt_slice = dt[entry_idx + 1 : exit_idx + 1]
            valid_dt = dt_slice[~np.isnan(dt_slice)]
            duration = float(valid_dt.sum()) if len(valid_dt) > 0 else 0.0
        else:
            duration = 0.0

        if duration < min_corner_duration_s:
            continue

        # Approximate corner distance
        if not np.isnan(distance[entry_idx]) and not np.isnan(distance[exit_idx]):
            corner_dist = distance[exit_idx] - distance[entry_idx]
        else:
            corner_dist = np.nan

        # Exit acceleration (mean accel from min to exit)
        exit_accel = np.nan
        if "acceleration_longitudinal" in df.columns and exit_idx > mi:
            accel_slice = df["acceleration_longitudinal"].iloc[mi:exit_idx + 1]
            valid_accel = accel_slice.dropna()
            if not valid_accel.empty:
                exit_accel = float(valid_accel.mean())

        corner_idx += 1
        corners.append({
            "corner_index": corner_idx,
            "corner_detection_method": "speed_profile_heuristic",
            "corner_entry_speed": entry_speed,
            "minimum_corner_speed": min_speed,
            "corner_exit_speed": exit_speed,
            "entry_to_min_speed_loss": speed_drop,
            "exit_acceleration": exit_accel,
            "corner_duration": duration,
            "approximate_corner_distance": corner_dist,
        })

    result = pd.DataFrame(corners)

    if not result.empty:
        # Scrub any inf
        numeric = result.select_dtypes(include=[np.number]).columns
        for col in numeric:
            mask = np.isinf(result[col])
            if mask.any():
                result.loc[mask, col] = np.nan

    return result
