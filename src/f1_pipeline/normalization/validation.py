"""Structural / data-quality validation for canonical datasets.

Severity levels
---------------
* **ERROR**   — structural failure; the dataset cannot be used.
* **WARNING** — missing optional columns or suspicious values.
* **INFO**    — statistics or informational notes (recorded in warnings list).

Policy: Do NOT reject valid F1 data because optional fields are absent.
"""
from __future__ import annotations

import pandas as pd

from f1_pipeline.normalization.schemas import QualityReport


# ---------------------------------------------------------------------------
# Laps validation
# ---------------------------------------------------------------------------
_LAP_REQUIRED_COLUMNS = {"driver_code", "lap_number", "lap_time"}
_LAP_EXPECTED_COLUMNS = {
    "team", "sector1_time", "sector2_time", "sector3_time",
    "compound", "tyre_life", "stint", "position",
}


def validate_laps(df: pd.DataFrame) -> QualityReport:
    """Validate a canonical laps DataFrame."""
    report = QualityReport(asset_type="laps", rows=len(df))

    if df.empty:
        report.errors.append("Laps DataFrame is empty.")
        report.valid = False
        return report

    # Required columns
    missing_req = _LAP_REQUIRED_COLUMNS - set(df.columns)
    if missing_req:
        report.errors.append(f"Missing required columns: {sorted(missing_req)}")
        report.missing_columns.extend(sorted(missing_req))
        report.valid = False

    # Expected (optional) columns
    missing_exp = _LAP_EXPECTED_COLUMNS - set(df.columns)
    if missing_exp:
        report.warnings.append(f"Missing optional columns: {sorted(missing_exp)}")
        report.missing_columns.extend(sorted(missing_exp))

    # Value checks (only when columns exist)
    if "lap_number" in df.columns:
        invalid_laps = df["lap_number"].dropna()
        if (invalid_laps <= 0).any():
            report.warnings.append("Some lap_number values are <= 0.")

    if "lap_time" in df.columns:
        valid_times = df["lap_time"].dropna()
        if (valid_times <= 0).any():
            report.warnings.append("Some lap_time values are <= 0 seconds.")

    return report


# ---------------------------------------------------------------------------
# Telemetry validation
# ---------------------------------------------------------------------------
_TELEM_REQUIRED_COLUMNS = {"speed"}
_TELEM_EXPECTED_CHANNELS = {"throttle", "brake", "rpm", "gear", "drs"}


def validate_telemetry(df: pd.DataFrame) -> QualityReport:
    """Validate a canonical telemetry DataFrame."""
    report = QualityReport(asset_type="telemetry", rows=len(df))

    if df.empty:
        report.errors.append("Telemetry DataFrame is empty.")
        report.valid = False
        return report

    missing_req = _TELEM_REQUIRED_COLUMNS - set(df.columns)
    if missing_req:
        report.errors.append(f"Missing required columns: {sorted(missing_req)}")
        report.missing_columns.extend(sorted(missing_req))
        report.valid = False

    missing_chan = _TELEM_EXPECTED_CHANNELS - set(df.columns)
    if missing_chan:
        report.warnings.append(f"Missing optional channels: {sorted(missing_chan)}")
        report.missing_columns.extend(sorted(missing_chan))

    if "speed" in df.columns:
        valid_speed = df["speed"].dropna()
        if len(valid_speed) > 0 and (valid_speed < 0).any():
            report.warnings.append("Some speed values are negative.")

    return report


# ---------------------------------------------------------------------------
# Weather validation
# ---------------------------------------------------------------------------
_WEATHER_REQUIRED_COLUMNS = {"time"}
_WEATHER_EXPECTED_COLUMNS = {
    "air_temperature", "track_temperature", "humidity",
    "pressure", "wind_speed",
}


def validate_weather(df: pd.DataFrame) -> QualityReport:
    """Validate a canonical weather DataFrame."""
    report = QualityReport(asset_type="weather", rows=len(df))

    if df.empty:
        report.errors.append("Weather DataFrame is empty.")
        report.valid = False
        return report

    missing_req = _WEATHER_REQUIRED_COLUMNS - set(df.columns)
    if missing_req:
        report.errors.append(f"Missing required columns: {sorted(missing_req)}")
        report.missing_columns.extend(sorted(missing_req))
        report.valid = False

    missing_exp = _WEATHER_EXPECTED_COLUMNS - set(df.columns)
    if missing_exp:
        report.warnings.append(f"Missing optional columns: {sorted(missing_exp)}")
        report.missing_columns.extend(sorted(missing_exp))

    return report
