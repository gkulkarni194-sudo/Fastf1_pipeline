"""Vehicle dynamics — lateral acceleration from trajectory data.

Lateral acceleration is computed via:

    a_lat = v · (dθ / dt)

where θ = arctan2(dy, dx) is the heading angle derived from x/y
position data.

If trajectory columns (``x``, ``y``) are absent or entirely NaN the
column is created but filled with NaN, and a warning is logged.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

KMH_TO_MS = 1.0 / 3.6


def compute_dynamics(
    df: pd.DataFrame,
    max_gap_seconds: float = 0.5,
) -> pd.DataFrame:
    """Compute lateral acceleration from trajectory and speed.

    Parameters
    ----------
    df:
        Telemetry DataFrame **after** ``compute_derivatives`` has run
        (must contain ``dt``).  Optionally contains ``x``, ``y``
        (trajectory) and ``speed`` (km/h).
    max_gap_seconds:
        Gaps larger than this invalidate the lateral-acceleration
        calculation.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with ``acceleration_lateral`` added.
    """
    out = df.copy()

    # Guard: need dt, x, y, and speed
    required = {"x", "y", "speed", "dt"}
    missing = required - set(out.columns)
    if missing:
        logger.warning(
            "Cannot compute lateral acceleration — missing columns: %s. "
            "Filling acceleration_lateral with NaN.",
            sorted(missing),
        )
        out["acceleration_lateral"] = np.nan
        return out

    # Check that x/y actually have usable (non-NaN) data
    if out["x"].isna().all() or out["y"].isna().all():
        logger.warning(
            "Trajectory columns x/y are entirely NaN. "
            "Filling acceleration_lateral with NaN."
        )
        out["acceleration_lateral"] = np.nan
        return out

    # ------------------------------------------------------------------
    # Validity mask (reuse dt already computed by derivatives)
    # ------------------------------------------------------------------
    invalid_dt = out["dt"].isna() | (out["dt"] <= 0) | (out["dt"] > max_gap_seconds)

    # ------------------------------------------------------------------
    # Heading angle θ = arctan2(dy, dx)
    # ------------------------------------------------------------------
    dx = out["x"].diff()
    dy = out["y"].diff()

    # Mask position deltas across invalid gaps
    dx = dx.where(~invalid_dt, other=np.nan)
    dy = dy.where(~invalid_dt, other=np.nan)

    theta = np.arctan2(dy.to_numpy(dtype=float, na_value=np.nan),
                       dx.to_numpy(dtype=float, na_value=np.nan))

    # Unwrap to avoid ±π jumps — only on non-NaN stretches
    theta_unwrapped = _safe_unwrap(theta)
    theta_series = pd.Series(theta_unwrapped, index=out.index)

    # ------------------------------------------------------------------
    # Angular velocity ω = dθ / dt
    # ------------------------------------------------------------------
    d_theta = theta_series.diff()
    omega = d_theta / out["dt"]

    # ------------------------------------------------------------------
    # Lateral acceleration a_lat = v · ω
    # ------------------------------------------------------------------
    speed_ms = out["speed"] * KMH_TO_MS
    out["acceleration_lateral"] = speed_ms * omega

    # Invalidate across large gaps (current and previous must be valid)
    prev_invalid = invalid_dt.shift(1, fill_value=True)
    out.loc[invalid_dt | prev_invalid, "acceleration_lateral"] = np.nan

    # Scrub any inf
    mask = np.isinf(out["acceleration_lateral"])
    if mask.any():
        out.loc[mask, "acceleration_lateral"] = np.nan

    return out


def _safe_unwrap(angles: np.ndarray) -> np.ndarray:
    """Unwrap an angle array that may contain NaN values.

    ``np.unwrap`` does not handle NaN gracefully in all NumPy versions,
    so we unwrap only the valid segments.
    """
    result = np.full_like(angles, np.nan, dtype=float)
    valid = ~np.isnan(angles)
    if valid.any():
        result[valid] = np.unwrap(angles[valid])
    return result
