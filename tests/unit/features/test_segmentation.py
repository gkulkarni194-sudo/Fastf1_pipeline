"""Unit tests for braking event and straight-line detection."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.features.telemetry.segmentation import (
    detect_braking_events,
    detect_straight_lines,
)


def _make_braking_telemetry() -> pd.DataFrame:
    """Create a telemetry trace with one clear braking event."""
    n = 40
    speed = np.concatenate([
        np.full(10, 300),    # high speed
        np.linspace(300, 100, 10),  # braking
        np.full(10, 100),   # low speed
        np.linspace(100, 300, 10),  # accelerating
    ])
    brake = np.concatenate([
        np.zeros(10),
        np.ones(10),  # braking
        np.zeros(10),
        np.zeros(10),
    ])
    dt = np.full(n, 0.1)
    dt[0] = np.nan
    distance = np.cumsum(speed / 3.6 * 0.1)
    time_s = np.cumsum(np.where(np.isnan(dt), 0, dt))

    return pd.DataFrame({
        "time": pd.to_timedelta(time_s, unit="s"),
        "speed": speed,
        "brake_active": brake.astype(bool),
        "distance": distance,
        "dt": dt,
        "acceleration_longitudinal": np.gradient(speed / 3.6, 0.1),
    })


class TestBrakingDetection:
    def test_detects_braking_event(self):
        df = _make_braking_telemetry()
        result = detect_braking_events(df, min_speed_drop_kmh=15.0, min_duration_s=0.25)
        assert len(result) >= 1
        assert "entry_speed" in result.columns
        assert result["entry_speed"].iloc[0] >= 250  # started around 300

    def test_speed_loss_filter(self):
        df = _make_braking_telemetry()
        # Set min drop very high — should filter out all events
        result = detect_braking_events(df, min_speed_drop_kmh=500.0)
        assert len(result) == 0

    def test_missing_columns_returns_empty(self):
        df = pd.DataFrame({"speed": [100, 200]})
        result = detect_braking_events(df)
        assert len(result) == 0

    def test_no_braking_returns_empty(self):
        df = pd.DataFrame({
            "time": pd.to_timedelta([0.0, 0.1, 0.2], unit="s"),
            "speed": [100, 100, 100],
            "brake_active": [False, False, False],
            "distance": [0, 10, 20],
            "dt": [np.nan, 0.1, 0.1],
        })
        result = detect_braking_events(df)
        assert len(result) == 0

    def test_braking_event_columns(self):
        df = _make_braking_telemetry()
        result = detect_braking_events(df, min_speed_drop_kmh=15.0)
        if not result.empty:
            expected_cols = {
                "braking_start_distance", "braking_end_distance",
                "braking_distance", "braking_duration", "entry_speed",
                "minimum_speed", "speed_loss", "peak_deceleration",
            }
            assert expected_cols.issubset(set(result.columns))


def _make_straight_telemetry() -> pd.DataFrame:
    """Create a trace with one long full-throttle straight."""
    n = 30
    return pd.DataFrame({
        "throttle_percent": np.concatenate([np.full(5, 50), np.full(20, 98), np.full(5, 30)]),
        "speed": np.concatenate([np.full(5, 200), np.full(20, 310), np.full(5, 200)]),
        "distance": np.arange(n) * 50.0,
        "dt": np.concatenate([[np.nan], np.full(n - 1, 0.1)]),
        "drs_active": np.concatenate([np.zeros(5), np.ones(20), np.zeros(5)]).astype(bool),
    })


class TestStraightLineDetection:
    def test_detects_straight(self):
        df = _make_straight_telemetry()
        result = detect_straight_lines(df, throttle_threshold=95.0, min_duration_s=0.5)
        assert len(result) >= 1

    def test_straight_columns(self):
        df = _make_straight_telemetry()
        result = detect_straight_lines(df, throttle_threshold=95.0, min_duration_s=0.5)
        if not result.empty:
            expected = {
                "straight_start_distance", "straight_end_distance",
                "straight_length", "time_at_full_throttle",
                "maximum_speed", "average_speed", "DRS_active_fraction",
            }
            assert expected.issubset(set(result.columns))

    def test_missing_columns_returns_empty(self):
        df = pd.DataFrame({"speed": [100]})
        result = detect_straight_lines(df)
        assert len(result) == 0

    def test_duration_filter(self):
        df = _make_straight_telemetry()
        result = detect_straight_lines(df, throttle_threshold=95.0, min_duration_s=100.0)
        assert len(result) == 0
