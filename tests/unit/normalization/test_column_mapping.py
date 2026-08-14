"""Tests for column_mapping module."""
from __future__ import annotations

import pandas as pd
import pytest

from f1_pipeline.normalization.column_mapping import (
    LAPS_COLUMN_MAP,
    TELEMETRY_COLUMN_MAP,
    WEATHER_COLUMN_MAP,
    apply_column_mapping,
)


class TestLapsColumnMapping:
    def test_renames_known_columns(self):
        df = pd.DataFrame({
            "Driver": ["VER", "HAM"],
            "LapNumber": [1, 2],
            "LapTime": [80.0, 81.0],
        })
        out = apply_column_mapping(df, LAPS_COLUMN_MAP)
        assert "driver_code" in out.columns
        assert "lap_number" in out.columns
        assert "lap_time" in out.columns
        assert "Driver" not in out.columns

    def test_preserves_unmapped_columns(self):
        df = pd.DataFrame({
            "Driver": ["VER"],
            "CustomExtra": [42],
        })
        out = apply_column_mapping(df, LAPS_COLUMN_MAP, preserve_unmapped=True)
        assert "driver_code" in out.columns
        # Unmapped columns are lowered
        assert "custom_extra" in out.columns

    def test_drops_unmapped_when_configured(self):
        df = pd.DataFrame({
            "Driver": ["VER"],
            "CustomExtra": [42],
        })
        out = apply_column_mapping(df, LAPS_COLUMN_MAP, preserve_unmapped=False)
        assert "driver_code" in out.columns
        assert "custom_extra" not in out.columns
        assert "CustomExtra" not in out.columns

    def test_injects_context_columns(self):
        df = pd.DataFrame({"Driver": ["VER"]})
        out = apply_column_mapping(
            df, LAPS_COLUMN_MAP,
            context={"season": 2024, "event_name": "Bahrain"},
        )
        assert out["season"].iloc[0] == 2024
        assert out["event_name"].iloc[0] == "Bahrain"

    def test_handles_missing_source_columns_gracefully(self):
        df = pd.DataFrame({"SomeOther": [1]})
        out = apply_column_mapping(df, LAPS_COLUMN_MAP)
        # No crash, original columns still present (lowered)
        assert "some_other" in out.columns


class TestTelemetryColumnMapping:
    def test_renames_telemetry_channels(self):
        df = pd.DataFrame({
            "Speed": [300], "Throttle": [100], "Brake": [0],
            "RPM": [12000], "nGear": [8], "DRS": [1],
        })
        out = apply_column_mapping(df, TELEMETRY_COLUMN_MAP)
        assert set(out.columns) == {"speed", "throttle", "brake", "rpm", "gear", "drs"}

    def test_gear_renamed_from_ngear(self):
        df = pd.DataFrame({"nGear": [7]})
        out = apply_column_mapping(df, TELEMETRY_COLUMN_MAP)
        assert "gear" in out.columns
        assert out["gear"].iloc[0] == 7


class TestWeatherColumnMapping:
    def test_renames_weather_fields(self):
        df = pd.DataFrame({
            "AirTemp": [25.0],
            "TrackTemp": [40.0],
            "Humidity": [50.0],
            "WindSpeed": [3.5],
        })
        out = apply_column_mapping(df, WEATHER_COLUMN_MAP)
        assert "air_temperature" in out.columns
        assert "track_temperature" in out.columns
        assert "humidity" in out.columns
        assert "wind_speed" in out.columns
