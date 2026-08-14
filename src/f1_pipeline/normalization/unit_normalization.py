"""Unit normalization for canonical datasets.

Policy
------
Only normalize units when the source unit is known **with confidence**.
Every conversion must be documented with source and canonical units.

FastF1 source units (documented / empirically verified)
------------------------------------------------------
* **speed**           : km/h  →  canonical **km/h** (no conversion)
* **throttle**        : 0–100 percentage  →  canonical 0–100 (no conversion)
* **brake**           : 0–100 or boolean (source-dependent) →  canonical 0–100
* **rpm**             : rev/min  →  canonical rev/min (no conversion)
* **air_temperature** : °C  →  canonical °C (no conversion)
* **track_temperature**: °C  →  canonical °C (no conversion)
* **humidity**        : %  →  canonical % (no conversion)
* **pressure**        : mbar  →  canonical mbar (no conversion)
* **wind_speed**      : m/s  →  canonical m/s (no conversion)
* **wind_direction**  : degrees (0-360)  →  canonical degrees (no conversion)
* **distance**        : metres  →  canonical metres (no conversion)
* **x, y, z**         : metres (track coordinates)  →  canonical metres

Because FastF1 already uses standard SI / industry units, this module is
currently a **documented no-op**.  The function exists so that future sources
with different units can be integrated without changing the pipeline structure.
"""
from __future__ import annotations

import pandas as pd


# ---------------------------------------------------------------------------
# Unit documentation registry (source_unit, canonical_unit, conversion)
# ---------------------------------------------------------------------------
UNIT_REGISTRY: dict[str, dict[str, str]] = {
    "speed":             {"source": "km/h",    "canonical": "km/h",    "conversion": "identity"},
    "throttle":          {"source": "0-100%",  "canonical": "0-100%",  "conversion": "identity"},
    "brake":             {"source": "0-100%",  "canonical": "0-100%",  "conversion": "identity"},
    "rpm":               {"source": "rev/min", "canonical": "rev/min", "conversion": "identity"},
    "distance":          {"source": "m",       "canonical": "m",       "conversion": "identity"},
    "x":                 {"source": "m",       "canonical": "m",       "conversion": "identity"},
    "y":                 {"source": "m",       "canonical": "m",       "conversion": "identity"},
    "z":                 {"source": "m",       "canonical": "m",       "conversion": "identity"},
    "air_temperature":   {"source": "°C",      "canonical": "°C",      "conversion": "identity"},
    "track_temperature": {"source": "°C",      "canonical": "°C",      "conversion": "identity"},
    "humidity":          {"source": "%",       "canonical": "%",       "conversion": "identity"},
    "pressure":          {"source": "mbar",    "canonical": "mbar",    "conversion": "identity"},
    "wind_speed":        {"source": "m/s",     "canonical": "m/s",     "conversion": "identity"},
    "wind_direction":    {"source": "degrees", "canonical": "degrees", "conversion": "identity"},
}


def apply_unit_normalization(df: pd.DataFrame, asset_type: str) -> pd.DataFrame:
    """Apply unit normalizations for the given *asset_type*.

    Currently a no-op because FastF1 uses the same units as our canonical
    representation.  Future sources (e.g. Ergast, timing sheets) may
    require conversions here.

    Parameters
    ----------
    df:
        Canonical DataFrame (after column + type normalization).
    asset_type:
        One of ``"laps"``, ``"telemetry"``, ``"weather"``.

    Returns
    -------
    pd.DataFrame
        The DataFrame with units normalized (unchanged for FastF1).
    """
    # Placeholder — add actual conversions when new sources are added.
    return df.copy()
