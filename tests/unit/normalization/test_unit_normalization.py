"""Tests for unit_normalization module."""
from __future__ import annotations

import pandas as pd

from f1_pipeline.normalization.unit_normalization import (
    UNIT_REGISTRY,
    apply_unit_normalization,
)


class TestUnitRegistry:
    def test_speed_documented(self):
        assert "speed" in UNIT_REGISTRY
        assert UNIT_REGISTRY["speed"]["source"] == "km/h"
        assert UNIT_REGISTRY["speed"]["canonical"] == "km/h"

    def test_temperature_documented(self):
        assert UNIT_REGISTRY["air_temperature"]["source"] == "°C"
        assert UNIT_REGISTRY["air_temperature"]["canonical"] == "°C"

    def test_pressure_documented(self):
        assert UNIT_REGISTRY["pressure"]["source"] == "mbar"

    def test_wind_speed_documented(self):
        assert UNIT_REGISTRY["wind_speed"]["source"] == "m/s"

    def test_all_conversions_are_identity(self):
        """FastF1 source units match canonical — all conversions are identity."""
        for field, info in UNIT_REGISTRY.items():
            assert info["conversion"] == "identity", f"{field} has non-identity conversion"


class TestApplyUnitNormalization:
    def test_returns_copy(self):
        df = pd.DataFrame({"speed": [300.0]})
        out = apply_unit_normalization(df, "telemetry")
        assert out is not df

    def test_values_unchanged_for_fastf1(self):
        df = pd.DataFrame({"speed": [300.0], "rpm": [12000.0]})
        out = apply_unit_normalization(df, "telemetry")
        assert out["speed"].iloc[0] == 300.0
        assert out["rpm"].iloc[0] == 12000.0
