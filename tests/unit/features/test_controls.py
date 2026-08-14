"""Unit tests for driver control normalisation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.features.telemetry.controls import compute_controls


class TestThrottle:
    def test_throttle_percent_clamped(self):
        df = pd.DataFrame({"throttle": [-5, 0, 50, 100, 110]})
        result = compute_controls(df)
        np.testing.assert_array_equal(result["throttle_percent"].values, [0, 0, 50, 100, 100])

    def test_missing_throttle_fills_nan(self):
        df = pd.DataFrame({"speed": [100, 200]})
        result = compute_controls(df)
        assert result["throttle_percent"].isna().all()


class TestBrake:
    def test_brake_active_bool(self):
        df = pd.DataFrame({"brake": [0, 1, 0, 100]})
        result = compute_controls(df)
        assert list(result["brake_active"]) == [False, True, False, True]

    def test_brake_intensity_passthrough(self):
        df = pd.DataFrame({"brake": [0, 50, 100]})
        result = compute_controls(df)
        # Values > 1 → pass-through as pressure/percentage
        np.testing.assert_array_equal(result["brake_intensity"].values, [0, 50, 100])

    def test_missing_brake_defaults_false(self):
        df = pd.DataFrame({"speed": [100]})
        result = compute_controls(df)
        assert result["brake_active"].iloc[0] == False
        assert result["brake_intensity"].iloc[0] == 0.0


class TestDRS:
    def test_drs_active_threshold(self):
        df = pd.DataFrame({"drs": [0, 1, 8, 10, 12, 14]})
        result = compute_controls(df)
        expected = [False, False, False, True, True, True]
        assert list(result["drs_active"]) == expected

    def test_missing_drs_defaults_false(self):
        df = pd.DataFrame({"speed": [100]})
        result = compute_controls(df)
        assert result["drs_active"].iloc[0] == False


class TestGear:
    def test_gear_passthrough(self):
        df = pd.DataFrame({"gear": [1, 2, 3, 4]})
        result = compute_controls(df)
        np.testing.assert_array_equal(result["gear"].values, [1, 2, 3, 4])

    def test_non_numeric_gear_coerced(self):
        df = pd.DataFrame({"gear": ["1", "N/A", "3"]})
        result = compute_controls(df)
        assert result["gear"].iloc[0] == 1.0
        assert np.isnan(result["gear"].iloc[1])


class TestCombined:
    def test_all_channels_present(self):
        df = pd.DataFrame({
            "throttle": [80],
            "brake": [0],
            "drs": [12],
            "gear": [7],
        })
        result = compute_controls(df)
        assert "throttle_percent" in result.columns
        assert "brake_active" in result.columns
        assert "brake_intensity" in result.columns
        assert "drs_active" in result.columns
        assert "gear" in result.columns
