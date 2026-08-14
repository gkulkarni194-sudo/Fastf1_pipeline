"""Type normalization for canonical datasets.

Key conversions
---------------
* ``pd.Timedelta`` → ``float`` seconds  (documented: source is HH:MM:SS.fff)
* Lap-specific integer columns → nullable ``Int64``
* Telemetry numeric channels → ``float64``
* Telemetry integer channels → nullable ``Int64``
* Weather numeric fields → ``float64``
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Timedelta → seconds
# ---------------------------------------------------------------------------
def timedelta_to_seconds(series: pd.Series) -> pd.Series:
    """Convert a series of ``pd.Timedelta`` (or compatible) to seconds.

    Source representation : ``Timedelta("0 days 00:01:23.456000")``
    Canonical representation : ``83.456`` (float64, seconds)

    ``NaT`` values become ``NaN``.
    """
    if pd.api.types.is_timedelta64_dtype(series):
        return series.dt.total_seconds().astype("float64")
    try:
        td = pd.to_timedelta(series, errors="coerce")
    except (TypeError, ValueError):
        # Series may contain NaT with datetime64 dtype — return NaN
        return pd.Series(np.nan, index=series.index, dtype="float64")
    return td.dt.total_seconds().astype("float64")


# ---------------------------------------------------------------------------
# Laps
# ---------------------------------------------------------------------------
_LAP_TIME_COLUMNS = [
    "lap_time",
    "sector1_time",
    "sector2_time",
    "sector3_time",
    "pit_in_time",
    "pit_out_time",
    "lap_start_time",
    "sector1_session_time",
    "sector2_session_time",
    "sector3_session_time",
]

_LAP_INT_COLUMNS = [
    "lap_number",
    "position",
    "stint",
    "tyre_life",
    "driver_number",
]


def normalize_lap_types(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize types for a canonical laps DataFrame."""
    out = df.copy()

    # Convert timedelta columns to seconds
    for col in _LAP_TIME_COLUMNS:
        if col in out.columns:
            out[col] = timedelta_to_seconds(out[col])

    # Integer columns — use nullable Int64 to preserve NaN
    for col in _LAP_INT_COLUMNS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")

    return out


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------
_TELEM_FLOAT_COLUMNS = ["speed", "throttle", "brake", "rpm", "distance",
                         "x", "y", "z"]
_TELEM_INT_COLUMNS = ["gear", "drs", "lap_number", "driver_number"]
_TELEM_TIME_COLUMNS = ["time", "session_time"]


def normalize_telemetry_types(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize types for a canonical telemetry DataFrame."""
    out = df.copy()

    for col in _TELEM_FLOAT_COLUMNS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")

    for col in _TELEM_INT_COLUMNS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")

    for col in _TELEM_TIME_COLUMNS:
        if col in out.columns and pd.api.types.is_timedelta64_dtype(out[col]):
            out[col] = timedelta_to_seconds(out[col])

    return out


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------
_WEATHER_FLOAT_COLUMNS = [
    "air_temperature",
    "track_temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "wind_direction",
]

_WEATHER_TIME_COLUMNS = ["time"]


def normalize_weather_types(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize types for a canonical weather DataFrame."""
    out = df.copy()

    for col in _WEATHER_FLOAT_COLUMNS:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")

    for col in _WEATHER_TIME_COLUMNS:
        if col in out.columns and pd.api.types.is_timedelta64_dtype(out[col]):
            out[col] = timedelta_to_seconds(out[col])

    # rainfall: keep as-is (boolean or numeric depending on source)
    if "rainfall" in out.columns:
        out["rainfall"] = pd.to_numeric(out["rainfall"], errors="coerce")

    return out
