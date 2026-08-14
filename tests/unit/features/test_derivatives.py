"""Unit tests for telemetry derivative calculations."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.features.telemetry.derivatives import compute_derivatives


# ======================================================================
# Helpers
# ======================================================================

def _make_telemetry(
    times_s: list[float],
    speeds_kmh: list[float],
    distances: list[float] | None = None,
) -> pd.DataFrame:
    """Build a minimal canonical telemetry DataFrame."""
    df = pd.DataFrame({
        "time": pd.to_timedelta(times_s, unit="s"),
        "speed": speeds_kmh,
    })
    if distances is not None:
        df["distance"] = distances
    return df


# ======================================================================
# Basic derivative tests
# ======================================================================

class TestDtCalculation:
    def test_uniform_dt(self):
        df = _make_telemetry([0.0, 0.1, 0.2, 0.3], [100, 100, 100, 100])
        result = compute_derivatives(df)
        # First row dt is NaN (no predecessor)
        assert np.isnan(result["dt"].iloc[0])
        np.testing.assert_allclose(result["dt"].iloc[1:].values, [0.1, 0.1, 0.1], atol=1e-9)

    def test_irregular_dt(self):
        df = _make_telemetry([0.0, 0.05, 0.2, 0.25], [100, 100, 100, 100])
        result = compute_derivatives(df)
        np.testing.assert_allclose(result["dt"].iloc[1:].values, [0.05, 0.15, 0.05], atol=1e-9)


class TestSpeedConversion:
    def test_speed_ms_conversion(self):
        df = _make_telemetry([0.0, 0.1], [360.0, 360.0])
        result = compute_derivatives(df)
        # 360 km/h = 100 m/s
        np.testing.assert_allclose(result["speed_ms"].values, [100.0, 100.0], atol=1e-9)

    def test_original_speed_preserved(self):
        df = _make_telemetry([0.0, 0.1], [200.0, 250.0])
        result = compute_derivatives(df)
        # Original speed column must be unchanged
        np.testing.assert_array_equal(result["speed"].values, [200.0, 250.0])


class TestAcceleration:
    def test_constant_speed_zero_acceleration(self):
        df = _make_telemetry([0.0, 0.1, 0.2, 0.3], [100, 100, 100, 100])
        result = compute_derivatives(df)
        valid_accel = result["acceleration_longitudinal"].iloc[1:]
        np.testing.assert_allclose(valid_accel.values, [0, 0, 0], atol=1e-6)

    def test_linear_speed_ramp(self):
        # Speed goes 0, 36, 72, 108 km/h → 0, 10, 20, 30 m/s
        # dt = 1.0s → a = 10 m/s²
        df = _make_telemetry([0.0, 1.0, 2.0, 3.0], [0, 36, 72, 108])
        result = compute_derivatives(df, max_gap_seconds=1.5)
        valid = result["acceleration_longitudinal"].dropna()
        np.testing.assert_allclose(valid.values, [10.0, 10.0, 10.0], atol=1e-6)

    def test_deceleration_is_negative(self):
        df = _make_telemetry([0.0, 1.0, 2.0], [108, 72, 36])
        result = compute_derivatives(df, max_gap_seconds=1.5)
        valid = result["acceleration_longitudinal"].dropna()
        assert all(v < 0 for v in valid.values)


class TestJerk:
    def test_constant_acceleration_zero_jerk(self):
        df = _make_telemetry([0.0, 1.0, 2.0, 3.0, 4.0], [0, 36, 72, 108, 144])
        result = compute_derivatives(df, max_gap_seconds=1.5)
        # Jerk should be ~0 for linearly increasing speed
        valid_jerk = result["jerk"].iloc[3:]  # need 2 valid accels
        np.testing.assert_allclose(valid_jerk.dropna().values, [0, 0], atol=1e-4)


# ======================================================================
# Gap handling
# ======================================================================

class TestGapHandling:
    def test_large_gap_produces_nan(self):
        # Gap of 2.0s exceeds default 0.5s threshold
        df = _make_telemetry([0.0, 0.1, 2.1, 2.2], [100, 100, 100, 100])
        result = compute_derivatives(df, max_gap_seconds=0.5)
        # Row at index 2 has dt=2.0 > 0.5 → NaN
        assert np.isnan(result["acceleration_longitudinal"].iloc[2])

    def test_zero_dt_produces_nan(self):
        df = _make_telemetry([0.0, 0.0, 0.1], [100, 200, 300])
        result = compute_derivatives(df)
        # dt=0 → acceleration should be NaN, not inf
        assert np.isnan(result["acceleration_longitudinal"].iloc[1])

    def test_negative_dt_produces_nan(self):
        df = _make_telemetry([0.0, 0.1, 0.05], [100, 100, 100])
        result = compute_derivatives(df)
        # Negative dt (time going backward) → NaN
        assert np.isnan(result["acceleration_longitudinal"].iloc[2])


# ======================================================================
# Edge cases
# ======================================================================

class TestEdgeCases:
    def test_empty_dataframe(self):
        df = pd.DataFrame({"time": pd.Series(dtype="timedelta64[ns]"), "speed": pd.Series(dtype=float)})
        result = compute_derivatives(df)
        assert len(result) == 0
        assert "dt" in result.columns
        assert "acceleration_longitudinal" in result.columns

    def test_single_row(self):
        df = _make_telemetry([0.0], [100])
        result = compute_derivatives(df)
        assert len(result) == 1
        assert np.isnan(result["dt"].iloc[0])

    def test_missing_speed_column(self):
        df = pd.DataFrame({"time": pd.to_timedelta([0.0, 0.1], unit="s")})
        result = compute_derivatives(df)
        assert "speed_ms" in result.columns
        assert result["speed_ms"].isna().all()

    def test_no_inf_in_output(self):
        # Force a potential div-by-zero scenario
        df = _make_telemetry([0.0, 0.0, 0.0, 0.1], [0, 100, 200, 300])
        result = compute_derivatives(df)
        float_cols = result.select_dtypes(include=[float, np.float64])
        assert not np.isinf(float_cols.values[~np.isnan(float_cols.values)]).any()


class TestDistanceDelta:
    def test_distance_delta_calculated(self):
        df = _make_telemetry([0.0, 0.1, 0.2], [100, 100, 100], [0, 10, 25])
        result = compute_derivatives(df)
        assert "distance_delta" in result.columns
        np.testing.assert_allclose(result["distance_delta"].iloc[1:].values, [10, 15], atol=1e-9)

    def test_missing_distance_column(self):
        df = _make_telemetry([0.0, 0.1, 0.2], [100, 100, 100])
        result = compute_derivatives(df)
        assert "distance_delta" in result.columns
        assert result["distance_delta"].isna().all()


class TestDuplicateTimestamps:
    def test_duplicate_timestamps_produce_nan(self):
        df = _make_telemetry([0.0, 0.1, 0.1, 0.2], [100, 110, 120, 130])
        result = compute_derivatives(df)
        # dt=0 at index 2 → acceleration should be NaN
        assert np.isnan(result["acceleration_longitudinal"].iloc[2])
