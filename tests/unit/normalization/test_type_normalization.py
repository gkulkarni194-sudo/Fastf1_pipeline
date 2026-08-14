"""Tests for type_normalization module."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.normalization.type_normalization import (
    normalize_lap_types,
    normalize_telemetry_types,
    normalize_weather_types,
    timedelta_to_seconds,
)


class TestTimedeltaToSeconds:
    def test_basic_conversion(self):
        series = pd.Series([pd.Timedelta("0 days 00:01:23.456000")])
        result = timedelta_to_seconds(series)
        assert abs(result.iloc[0] - 83.456) < 1e-6

    def test_nat_becomes_nan(self):
        series = pd.Series([pd.NaT])
        result = timedelta_to_seconds(series)
        assert pd.isna(result.iloc[0])

    def test_zero_timedelta(self):
        series = pd.Series([pd.Timedelta(0)])
        result = timedelta_to_seconds(series)
        assert result.iloc[0] == 0.0

    def test_large_timedelta(self):
        series = pd.Series([pd.Timedelta("0 days 01:30:00")])
        result = timedelta_to_seconds(series)
        assert abs(result.iloc[0] - 5400.0) < 1e-6

    def test_mixed_valid_and_nat(self):
        series = pd.Series([pd.Timedelta("00:01:30"), pd.NaT, pd.Timedelta("00:00:45")])
        result = timedelta_to_seconds(series)
        assert abs(result.iloc[0] - 90.0) < 1e-6
        assert pd.isna(result.iloc[1])
        assert abs(result.iloc[2] - 45.0) < 1e-6


class TestNormalizeLapTypes:
    def test_timedelta_columns_converted(self):
        df = pd.DataFrame({
            "lap_time": [pd.Timedelta("00:01:23.456")],
            "sector1_time": [pd.Timedelta("00:00:28.123")],
            "lap_number": [1],
        })
        out = normalize_lap_types(df)
        assert out["lap_time"].dtype == np.float64
        assert abs(out["lap_time"].iloc[0] - 83.456) < 1e-3
        assert abs(out["sector1_time"].iloc[0] - 28.123) < 1e-3

    def test_integer_columns_nullable(self):
        df = pd.DataFrame({
            "lap_number": [1, 2, None],
            "position": [3, None, 1],
        })
        out = normalize_lap_types(df)
        assert str(out["lap_number"].dtype) == "Int64"
        assert str(out["position"].dtype) == "Int64"
        assert pd.isna(out["lap_number"].iloc[2])

    def test_missing_columns_no_crash(self):
        df = pd.DataFrame({"other_col": [1]})
        out = normalize_lap_types(df)
        assert "other_col" in out.columns


class TestNormalizeTelemetryTypes:
    def test_float_channels(self):
        df = pd.DataFrame({
            "speed": ["300", "280"],
            "throttle": [100, 80],
            "rpm": [12000, 11000],
        })
        out = normalize_telemetry_types(df)
        assert out["speed"].dtype == np.float64
        assert out["throttle"].dtype == np.float64

    def test_integer_channels(self):
        df = pd.DataFrame({"gear": [7, 8, None], "drs": [0, 1, None]})
        out = normalize_telemetry_types(df)
        assert str(out["gear"].dtype) == "Int64"
        assert str(out["drs"].dtype) == "Int64"

    def test_invalid_numeric_becomes_nan(self):
        df = pd.DataFrame({"speed": ["fast", "300"]})
        out = normalize_telemetry_types(df)
        assert pd.isna(out["speed"].iloc[0])
        assert out["speed"].iloc[1] == 300.0


class TestNormalizeWeatherTypes:
    def test_float_fields(self):
        df = pd.DataFrame({
            "air_temperature": [25.0],
            "track_temperature": [40.0],
            "humidity": [50],
        })
        out = normalize_weather_types(df)
        assert out["air_temperature"].dtype == np.float64
        assert out["humidity"].dtype == np.float64
