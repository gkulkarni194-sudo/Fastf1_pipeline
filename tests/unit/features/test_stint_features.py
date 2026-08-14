"""Unit tests for stint feature computation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.features.laps.stint_features import compute_stint_features


def _make_laps() -> pd.DataFrame:
    return pd.DataFrame({
        "driver_code": ["VER"] * 5 + ["HAM"] * 3,
        "stint": [1, 1, 1, 2, 2, 1, 1, 1],
        "lap_number": [1, 2, 3, 4, 5, 1, 2, 3],
        "lap_time": pd.to_timedelta([90, 88, 89, 91, 90, 92, 91, 90], unit="s"),
        "compound": ["SOFT"] * 3 + ["MEDIUM"] * 2 + ["HARD"] * 3,
        "tyre_life": [1, 2, 3, 1, 2, 1, 2, 3],
    })


class TestStintAggregation:
    def test_stint_count(self):
        laps = _make_laps()
        result = compute_stint_features(laps)
        # VER has 2 stints, HAM has 1 → 3 total
        assert len(result) == 3

    def test_stint_fields(self):
        laps = _make_laps()
        result = compute_stint_features(laps)
        expected = {
            "driver_code", "stint_number", "compound",
            "starting_lap", "ending_lap", "stint_length",
            "mean_lap_time", "best_lap_time", "median_lap_time",
            "lap_time_std", "mean_speed",
            "tyre_life_start", "tyre_life_end",
        }
        assert expected.issubset(set(result.columns))

    def test_best_lap_time(self):
        laps = _make_laps()
        result = compute_stint_features(laps)
        ver_s1 = result[(result["driver_code"] == "VER") & (result["stint_number"] == 1)]
        assert not ver_s1.empty
        assert ver_s1["best_lap_time"].iloc[0] == 88.0

    def test_stint_length(self):
        laps = _make_laps()
        result = compute_stint_features(laps)
        ver_s1 = result[(result["driver_code"] == "VER") & (result["stint_number"] == 1)]
        assert ver_s1["stint_length"].iloc[0] == 3

    def test_tyre_life(self):
        laps = _make_laps()
        result = compute_stint_features(laps)
        ver_s1 = result[(result["driver_code"] == "VER") & (result["stint_number"] == 1)]
        assert ver_s1["tyre_life_start"].iloc[0] == 1
        assert ver_s1["tyre_life_end"].iloc[0] == 3


class TestStintMeanSpeed:
    def test_mean_speed_from_telemetry(self):
        laps = _make_laps()
        telem = pd.DataFrame({
            "driver_code": ["VER"] * 6,
            "lap_number": [1, 1, 2, 2, 3, 3],
            "speed": [200, 250, 220, 260, 210, 240],
        })
        result = compute_stint_features(laps, telemetry_df=telem)
        ver_s1 = result[(result["driver_code"] == "VER") & (result["stint_number"] == 1)]
        assert ver_s1["mean_speed"].notna().all()

    def test_mean_speed_none_without_telemetry(self):
        laps = _make_laps()
        result = compute_stint_features(laps)
        assert result["mean_speed"].isna().all()


class TestStintEdgeCases:
    def test_missing_required_columns(self):
        df = pd.DataFrame({"speed": [100]})
        result = compute_stint_features(df)
        assert len(result) == 0

    def test_single_lap_stint(self):
        laps = pd.DataFrame({
            "driver_code": ["VER"],
            "stint": [1],
            "lap_number": [1],
            "lap_time": pd.to_timedelta([90], unit="s"),
            "compound": ["SOFT"],
        })
        result = compute_stint_features(laps)
        assert len(result) == 1
        # std should be None for single lap
        assert result["lap_time_std"].iloc[0] is None
