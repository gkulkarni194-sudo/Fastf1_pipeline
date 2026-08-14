"""Tests for canonicalizer module (full pipeline per asset type)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from f1_pipeline.normalization.canonicalizer import (
    canonicalize_laps,
    canonicalize_telemetry,
    canonicalize_weather,
)


class TestCanonicalizeLaps:
    def _sample_raw(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Driver": ["VER", "HAM", "VER"],
            "Team": ["Red Bull", "Mercedes", "Red Bull"],
            "LapNumber": [1, 1, 1],  # VER duplicate
            "LapTime": [
                pd.Timedelta("00:01:23.456"),
                pd.Timedelta("00:01:24.789"),
                pd.Timedelta("00:01:23.456"),
            ],
            "Compound": ["SOFT", "MEDIUM", "SOFT"],
        })

    def test_columns_renamed(self):
        df, quality, dup = canonicalize_laps(
            self._sample_raw(), season=2024, event_name="Bahrain", session_type="Q",
        )
        assert "driver_code" in df.columns
        assert "lap_time" in df.columns
        assert "Driver" not in df.columns

    def test_types_normalized(self):
        df, _, _ = canonicalize_laps(
            self._sample_raw(), season=2024, event_name="Bahrain", session_type="Q",
        )
        assert df["lap_time"].dtype == np.float64
        assert abs(df["lap_time"].iloc[0] - 83.456) < 1e-3

    def test_duplicates_detected(self):
        df, _, dup = canonicalize_laps(
            self._sample_raw(), season=2024, event_name="Bahrain", session_type="Q",
        )
        assert dup.duplicates_found == 1  # VER lap 1 duplicated
        assert dup.rows_before == 3
        assert dup.rows_after == 2

    def test_quality_valid(self):
        _, quality, _ = canonicalize_laps(
            self._sample_raw(), season=2024, event_name="Bahrain", session_type="Q",
        )
        assert quality.valid is True

    def test_context_injected(self):
        df, _, _ = canonicalize_laps(
            self._sample_raw(), season=2024, event_name="Bahrain", session_type="Q",
        )
        assert "season" in df.columns
        assert df["season"].iloc[0] == 2024

    def test_deterministic(self):
        raw = self._sample_raw()
        df1, _, _ = canonicalize_laps(raw, season=2024, event_name="Bahrain", session_type="Q")
        df2, _, _ = canonicalize_laps(raw, season=2024, event_name="Bahrain", session_type="Q")
        pd.testing.assert_frame_equal(df1, df2)


class TestCanonicalizeTelemetry:
    def _sample_raw(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Speed": [300.0, 280.0],
            "Throttle": [100, 80],
            "Brake": [0, 50],
            "RPM": [12000, 11000],
            "nGear": [8, 7],
            "DRS": [1, 0],
        })

    def test_columns_renamed(self):
        df, _, _ = canonicalize_telemetry(
            self._sample_raw(), season=2024, event_name="Bahrain",
            session_type="Q", driver_code="VER",
        )
        assert "speed" in df.columns
        assert "gear" in df.columns
        assert "nGear" not in df.columns

    def test_types_correct(self):
        df, _, _ = canonicalize_telemetry(
            self._sample_raw(), season=2024, event_name="Bahrain",
            session_type="Q",
        )
        assert df["speed"].dtype == np.float64
        assert str(df["gear"].dtype) == "Int64"


class TestCanonicalizeWeather:
    def _sample_raw(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Time": [pd.Timedelta("00:00:00"), pd.Timedelta("00:01:00")],
            "AirTemp": [25.0, 26.0],
            "TrackTemp": [40.0, 41.0],
            "Humidity": [50.0, 48.0],
            "Pressure": [1013.0, 1012.0],
            "WindSpeed": [3.5, 4.0],
            "WindDirection": [180, 190],
            "Rainfall": [False, False],
        })

    def test_columns_renamed(self):
        df, _, _ = canonicalize_weather(
            self._sample_raw(), season=2024, event_name="Bahrain", session_type="Q",
        )
        assert "air_temperature" in df.columns
        assert "wind_speed" in df.columns
        assert "AirTemp" not in df.columns

    def test_quality_valid(self):
        _, quality, _ = canonicalize_weather(
            self._sample_raw(), season=2024, event_name="Bahrain", session_type="Q",
        )
        assert quality.valid is True
