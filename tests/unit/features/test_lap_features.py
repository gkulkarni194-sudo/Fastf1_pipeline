"""Unit tests for lap feature computation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.features.laps.lap_features import compute_lap_features


def _make_laps() -> pd.DataFrame:
    return pd.DataFrame({
        "driver_code": ["VER", "VER", "VER"],
        "lap_number": [1, 2, 3],
        "lap_time": pd.to_timedelta([90, 88, 89], unit="s"),
        "sector1_time": pd.to_timedelta([30, 29, 30], unit="s"),
        "sector2_time": pd.to_timedelta([30, 29, 29], unit="s"),
        "sector3_time": pd.to_timedelta([30, 30, 30], unit="s"),
        "compound": ["SOFT", "SOFT", "SOFT"],
        "stint": [1, 1, 1],
        "tyre_life": [1, 2, 3],
    })


def _make_telemetry() -> pd.DataFrame:
    rows = []
    for lap in [1, 2, 3]:
        for i in range(10):
            rows.append({
                "driver_code": "VER",
                "lap_number": lap,
                "speed": 200 + i * 10,
                "acceleration_longitudinal": 2.0 + i * 0.5,
                "throttle_percent": 80 + i,
                "brake_active": i < 3,
                "drs_active": i > 7,
            })
    return pd.DataFrame(rows)


class TestLapTimeSeconds:
    def test_lap_time_seconds_derived(self):
        laps = _make_laps()
        result = compute_lap_features(laps)
        assert "lap_time_seconds" in result.columns
        np.testing.assert_allclose(result["lap_time_seconds"].values, [90, 88, 89])

    def test_original_lap_time_preserved(self):
        laps = _make_laps()
        result = compute_lap_features(laps)
        assert "lap_time" in result.columns
        assert pd.api.types.is_timedelta64_dtype(result["lap_time"])


class TestTelemetryAggregation:
    def test_max_speed_per_lap(self):
        laps = _make_laps()
        telem = _make_telemetry()
        result = compute_lap_features(laps, telemetry_df=telem)
        assert "maximum_speed" in result.columns
        assert result["maximum_speed"].notna().all()

    def test_throttle_fraction(self):
        laps = _make_laps()
        telem = _make_telemetry()
        result = compute_lap_features(laps, telemetry_df=telem)
        assert "throttle_fraction" in result.columns
        # Should be between 0 and 1
        assert (result["throttle_fraction"].dropna() <= 1.0).all()
        assert (result["throttle_fraction"].dropna() >= 0.0).all()


class TestBrakingCornerCounts:
    def test_braking_count_from_events(self):
        laps = _make_laps()
        braking = pd.DataFrame({
            "entry_speed": [300, 280],
            "minimum_speed": [100, 90],
        })
        result = compute_lap_features(laps, braking_events_df=braking)
        assert "number_of_braking_events" in result.columns
        assert result["number_of_braking_events"].iloc[0] == 2

    def test_corner_count(self):
        laps = _make_laps()
        corners = pd.DataFrame({
            "corner_index": [1, 2, 3],
            "minimum_corner_speed": [80, 120, 100],
        })
        result = compute_lap_features(laps, corners_df=corners)
        assert result["number_of_detected_corners"].iloc[0] == 3

    def test_no_events_gives_nan(self):
        laps = _make_laps()
        result = compute_lap_features(laps)
        assert result["number_of_braking_events"].isna().all()
        assert result["number_of_detected_corners"].isna().all()


class TestEdgeCases:
    def test_empty_laps(self):
        laps = pd.DataFrame(columns=["driver_code", "lap_number", "lap_time"])
        result = compute_lap_features(laps)
        assert len(result) == 0

    def test_no_telemetry(self):
        laps = _make_laps()
        result = compute_lap_features(laps, telemetry_df=None)
        assert "lap_time_seconds" in result.columns
