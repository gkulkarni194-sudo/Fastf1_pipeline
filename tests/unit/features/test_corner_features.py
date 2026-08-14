"""Unit tests for corner detection."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.features.corners.corner_features import detect_corners


def _make_corner_telemetry() -> pd.DataFrame:
    """Create a speed profile with one clear corner (V shape)."""
    # Straight → brake → apex → accelerate → straight
    speed = np.concatenate([
        np.full(5, 300),              # straight
        np.linspace(300, 100, 10),    # entry / braking
        np.full(3, 100),             # apex
        np.linspace(100, 280, 10),   # exit
        np.full(5, 280),             # straight
    ])
    n = len(speed)
    dt = np.full(n, 0.1)
    dt[0] = np.nan
    distance = np.cumsum(speed / 3.6 * 0.1)
    accel = np.gradient(speed / 3.6, 0.1)

    return pd.DataFrame({
        "speed": speed,
        "distance": distance,
        "dt": dt,
        "acceleration_longitudinal": accel,
    })


class TestCornerDetection:
    def test_detects_corner(self):
        df = _make_corner_telemetry()
        result = detect_corners(df, min_speed_drop_kmh=30.0, min_corner_duration_s=0.1)
        assert len(result) >= 1

    def test_corner_marked_as_heuristic(self):
        df = _make_corner_telemetry()
        result = detect_corners(df, min_speed_drop_kmh=30.0, min_corner_duration_s=0.1)
        if not result.empty:
            assert result["corner_detection_method"].iloc[0] == "speed_profile_heuristic"

    def test_corner_has_expected_columns(self):
        df = _make_corner_telemetry()
        result = detect_corners(df, min_speed_drop_kmh=30.0, min_corner_duration_s=0.1)
        if not result.empty:
            expected = {
                "corner_index", "corner_detection_method",
                "corner_entry_speed", "minimum_corner_speed",
                "corner_exit_speed", "entry_to_min_speed_loss",
                "exit_acceleration", "corner_duration",
                "approximate_corner_distance",
            }
            assert expected.issubset(set(result.columns))

    def test_speed_drop_filter(self):
        df = _make_corner_telemetry()
        # Require impossibly large speed drop
        result = detect_corners(df, min_speed_drop_kmh=500.0)
        assert len(result) == 0

    def test_entry_speed_greater_than_min_speed(self):
        df = _make_corner_telemetry()
        result = detect_corners(df, min_speed_drop_kmh=30.0, min_corner_duration_s=0.1)
        if not result.empty:
            for _, row in result.iterrows():
                assert row["corner_entry_speed"] > row["minimum_corner_speed"]


class TestCornerEdgeCases:
    def test_missing_columns_returns_empty(self):
        df = pd.DataFrame({"something": [1, 2, 3]})
        result = detect_corners(df)
        assert len(result) == 0

    def test_too_few_rows(self):
        df = pd.DataFrame({"speed": [100, 200], "distance": [0, 10], "dt": [np.nan, 0.1]})
        result = detect_corners(df)
        assert len(result) == 0

    def test_constant_speed_no_corners(self):
        df = pd.DataFrame({
            "speed": np.full(20, 200.0),
            "distance": np.arange(20) * 10.0,
            "dt": np.concatenate([[np.nan], np.full(19, 0.1)]),
        })
        result = detect_corners(df, min_speed_drop_kmh=30.0)
        assert len(result) == 0

    def test_no_inf_in_output(self):
        df = _make_corner_telemetry()
        result = detect_corners(df, min_speed_drop_kmh=30.0, min_corner_duration_s=0.1)
        if not result.empty:
            numeric = result.select_dtypes(include=[np.number])
            assert not np.isinf(numeric.values[~np.isnan(numeric.values)]).any()
