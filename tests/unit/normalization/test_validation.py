"""Tests for validation module."""
from __future__ import annotations

import pandas as pd

from f1_pipeline.normalization.validation import (
    validate_laps,
    validate_telemetry,
    validate_weather,
)


class TestValidateLaps:
    def test_valid_laps(self):
        df = pd.DataFrame({
            "driver_code": ["VER", "HAM"],
            "lap_number": [1, 2],
            "lap_time": [83.0, 84.0],
            "team": ["RBR", "MER"],
        })
        report = validate_laps(df)
        assert report.valid is True
        assert report.rows == 2
        assert len(report.errors) == 0

    def test_empty_laps_is_error(self):
        df = pd.DataFrame()
        report = validate_laps(df)
        assert report.valid is False
        assert any("empty" in e.lower() for e in report.errors)

    def test_missing_required_columns(self):
        df = pd.DataFrame({"other": [1]})
        report = validate_laps(df)
        assert report.valid is False
        assert len(report.missing_columns) > 0

    def test_missing_optional_columns_is_warning(self):
        df = pd.DataFrame({
            "driver_code": ["VER"],
            "lap_number": [1],
            "lap_time": [83.0],
        })
        report = validate_laps(df)
        assert report.valid is True
        assert len(report.warnings) > 0  # optional cols missing
        assert "team" in report.missing_columns

    def test_negative_lap_time_warning(self):
        df = pd.DataFrame({
            "driver_code": ["VER"],
            "lap_number": [1],
            "lap_time": [-5.0],
        })
        report = validate_laps(df)
        assert any("lap_time" in w for w in report.warnings)


class TestValidateTelemetry:
    def test_valid_telemetry(self):
        df = pd.DataFrame({
            "speed": [300.0, 280.0],
            "throttle": [100, 80],
            "brake": [0, 50],
            "rpm": [12000, 11000],
            "gear": [8, 7],
            "drs": [1, 0],
        })
        report = validate_telemetry(df)
        assert report.valid is True

    def test_empty_telemetry_is_error(self):
        df = pd.DataFrame()
        report = validate_telemetry(df)
        assert report.valid is False

    def test_missing_speed_is_error(self):
        df = pd.DataFrame({"throttle": [100]})
        report = validate_telemetry(df)
        assert report.valid is False

    def test_missing_optional_channels_is_warning(self):
        df = pd.DataFrame({"speed": [300.0]})
        report = validate_telemetry(df)
        assert report.valid is True
        assert len(report.warnings) > 0


class TestValidateWeather:
    def test_valid_weather(self):
        df = pd.DataFrame({
            "time": [0.0],
            "air_temperature": [25.0],
            "track_temperature": [40.0],
        })
        report = validate_weather(df)
        assert report.valid is True

    def test_empty_weather_is_error(self):
        report = validate_weather(pd.DataFrame())
        assert report.valid is False

    def test_missing_time_is_error(self):
        df = pd.DataFrame({"air_temperature": [25.0]})
        report = validate_weather(df)
        assert report.valid is False
