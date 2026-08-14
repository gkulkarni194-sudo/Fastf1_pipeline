"""Unit tests for lateral acceleration (dynamics)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.features.telemetry.dynamics import compute_dynamics


def _make_telem_with_trajectory(
    times_s: list[float],
    speeds_kmh: list[float],
    x: list[float],
    y: list[float],
) -> pd.DataFrame:
    dt_vals = [np.nan] + [times_s[i] - times_s[i - 1] for i in range(1, len(times_s))]
    return pd.DataFrame({
        "time": pd.to_timedelta(times_s, unit="s"),
        "speed": speeds_kmh,
        "x": x,
        "y": y,
        "dt": dt_vals,
    })


class TestLateralAcceleration:
    def test_straight_line_zero_lateral_accel(self):
        """Moving in a straight line should have ~0 lateral acceleration."""
        df = _make_telem_with_trajectory(
            [0.0, 0.1, 0.2, 0.3, 0.4],
            [100, 100, 100, 100, 100],
            [0, 10, 20, 30, 40],
            [0, 0, 0, 0, 0],
        )
        result = compute_dynamics(df)
        valid = result["acceleration_lateral"].dropna()
        np.testing.assert_allclose(valid.values, 0, atol=1.0)

    def test_turning_produces_nonzero_lateral_accel(self):
        """A circular arc should produce nonzero lateral acceleration."""
        n = 20
        angles = np.linspace(0, np.pi / 2, n)
        R = 50.0
        x = (R * np.cos(angles)).tolist()
        y = (R * np.sin(angles)).tolist()
        times = np.linspace(0, 2, n).tolist()
        speeds = [100.0] * n
        df = _make_telem_with_trajectory(times, speeds, x, y)
        result = compute_dynamics(df)
        valid = result["acceleration_lateral"].dropna()
        assert len(valid) > 0
        # At least some non-zero values
        assert (valid.abs() > 0.1).any()


class TestMissingTrajectory:
    def test_missing_x_y_fills_nan(self):
        """Without x/y, lateral accel should be NaN."""
        df = pd.DataFrame({
            "time": pd.to_timedelta([0.0, 0.1, 0.2], unit="s"),
            "speed": [100.0, 100.0, 100.0],
            "dt": [np.nan, 0.1, 0.1],
        })
        result = compute_dynamics(df)
        assert "acceleration_lateral" in result.columns
        assert result["acceleration_lateral"].isna().all()

    def test_all_nan_x_y_fills_nan(self):
        df = pd.DataFrame({
            "time": pd.to_timedelta([0.0, 0.1, 0.2], unit="s"),
            "speed": [100.0, 100.0, 100.0],
            "x": [np.nan, np.nan, np.nan],
            "y": [np.nan, np.nan, np.nan],
            "dt": [np.nan, 0.1, 0.1],
        })
        result = compute_dynamics(df)
        assert result["acceleration_lateral"].isna().all()


class TestGapHandling:
    def test_large_gap_invalidates_lateral_accel(self):
        df = _make_telem_with_trajectory(
            [0.0, 0.1, 2.0, 2.1],
            [100, 100, 100, 100],
            [0, 10, 500, 510],
            [0, 0, 0, 0],
        )
        result = compute_dynamics(df, max_gap_seconds=0.5)
        # Row at index 2 has dt=1.9s > 0.5 → lateral accel NaN
        assert np.isnan(result["acceleration_lateral"].iloc[2])


class TestNoInfOutput:
    def test_no_inf_in_lateral_accel(self):
        df = _make_telem_with_trajectory(
            [0.0, 0.0, 0.1],
            [100, 100, 100],
            [0, 0, 10],
            [0, 0, 0],
        )
        result = compute_dynamics(df)
        vals = result["acceleration_lateral"].dropna().values
        assert not np.isinf(vals).any()
