"""Explicit source → canonical column mappings.

Every rename is documented here.  Unmapped source columns are preserved by
default (controlled by the ``preserve_unmapped_columns`` configuration flag).
"""
from __future__ import annotations

from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Laps: FastF1 → canonical
# ---------------------------------------------------------------------------
LAPS_COLUMN_MAP: dict[str, str] = {
    "Driver": "driver_code",
    "Team": "team",
    "LapNumber": "lap_number",
    "LapTime": "lap_time",
    "Sector1Time": "sector1_time",
    "Sector2Time": "sector2_time",
    "Sector3Time": "sector3_time",
    "Compound": "compound",
    "TyreLife": "tyre_life",
    "Stint": "stint",
    "PitInTime": "pit_in_time",
    "PitOutTime": "pit_out_time",
    "IsPersonalBest": "is_personal_best",
    "Position": "position",
    "FreshTyre": "fresh_tyre",
    "TrackStatus": "track_status",
    "IsAccurate": "is_accurate",
    "LapStartTime": "lap_start_time",
    "LapStartDate": "lap_start_date",
    "Sector1SessionTime": "sector1_session_time",
    "Sector2SessionTime": "sector2_session_time",
    "Sector3SessionTime": "sector3_session_time",
    "SpeedI1": "speed_i1",
    "SpeedI2": "speed_i2",
    "SpeedFL": "speed_fl",
    "SpeedST": "speed_st",
    "DriverNumber": "driver_number",
}

# ---------------------------------------------------------------------------
# Telemetry: FastF1 car-data → canonical
# ---------------------------------------------------------------------------
TELEMETRY_COLUMN_MAP: dict[str, str] = {
    "Time": "time",
    "Date": "date",
    "Distance": "distance",
    "Speed": "speed",
    "Throttle": "throttle",
    "Brake": "brake",
    "RPM": "rpm",
    "nGear": "gear",
    "DRS": "drs",
    "X": "x",
    "Y": "y",
    "Z": "z",
    "Driver": "driver_code",
    "LapNumber": "lap_number",
    "DriverNumber": "driver_number",
    "SessionTime": "session_time",
}

# ---------------------------------------------------------------------------
# Weather: FastF1 → canonical
# ---------------------------------------------------------------------------
WEATHER_COLUMN_MAP: dict[str, str] = {
    "Time": "time",
    "AirTemp": "air_temperature",
    "TrackTemp": "track_temperature",
    "Humidity": "humidity",
    "Pressure": "pressure",
    "WindSpeed": "wind_speed",
    "WindDirection": "wind_direction",
    "Rainfall": "rainfall",
}

# ---------------------------------------------------------------------------
# Mapping of asset_type → column map for convenience
# ---------------------------------------------------------------------------
COLUMN_MAPS: dict[str, dict[str, str]] = {
    "laps": LAPS_COLUMN_MAP,
    "telemetry": TELEMETRY_COLUMN_MAP,
    "weather": WEATHER_COLUMN_MAP,
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
def apply_column_mapping(
    df: pd.DataFrame,
    mapping: dict[str, str],
    *,
    preserve_unmapped: bool = True,
    context: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Rename columns using *mapping* and optionally inject context columns.

    Parameters
    ----------
    df:
        The source DataFrame (not mutated).
    mapping:
        ``{SourceColumn: canonical_column}`` mapping.
    preserve_unmapped:
        If ``True``, columns not listed in *mapping* are kept with
        lowered-snake-case names.  If ``False`` they are dropped.
    context:
        Extra columns to inject (e.g. ``{"season": 2024}``).

    Returns
    -------
    pd.DataFrame
    """
    out = df.copy()

    # Rename mapped columns
    rename = {src: dst for src, dst in mapping.items() if src in out.columns}
    out = out.rename(columns=rename)

    if not preserve_unmapped:
        out = out[[c for c in out.columns if c in rename.values()]]
    else:
        # Lower-snake-case any remaining non-canonical columns
        unmapped_rename = {}
        canonical_names = set(rename.values())
        for col in out.columns:
            if col not in canonical_names:
                new = _to_snake_case(col)
                if new != col:
                    unmapped_rename[col] = new
        if unmapped_rename:
            out = out.rename(columns=unmapped_rename)

    # Inject context
    if context:
        for key, value in context.items():
            out[key] = value

    return out


def _to_snake_case(name: str) -> str:
    """Best-effort CamelCase / PascalCase → snake_case."""
    import re
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()
