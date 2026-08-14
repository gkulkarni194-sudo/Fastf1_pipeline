"""Unit tests for feature validation and quality reporting."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.features.validation import validate_features


class TestInfReplacement:
    def test_inf_replaced_with_nan(self):
        df = pd.DataFrame({
            "a": [1.0, np.inf, 3.0],
            "b": [4.0, 5.0, -np.inf],
        })
        cleaned, report = validate_features(df, "test")
        assert not np.isinf(cleaned.values).any()
        assert np.isnan(cleaned["a"].iloc[1])
        assert np.isnan(cleaned["b"].iloc[2])

    def test_inf_counts_in_report(self):
        df = pd.DataFrame({
            "x": [np.inf, -np.inf, 1.0],
        })
        _, report = validate_features(df, "test")
        assert report.invalid_values_count.get("x", 0) == 2


class TestQualityReport:
    def test_report_fields(self):
        df = pd.DataFrame({"a": [1.0, 2.0, np.nan], "b": ["x", "y", "z"]})
        _, report = validate_features(df, "telemetry")
        assert report.asset_type == "telemetry"
        assert report.valid is True
        assert report.rows_input == 3
        assert report.rows_output == 3
        assert "a" in report.features_created
        assert report.missing_feature_counts.get("a", 0) == 1

    def test_duplicate_count(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [10, 10, 20]})
        _, report = validate_features(df, "test")
        assert report.duplicate_count == 1

    def test_warnings_for_inf(self):
        df = pd.DataFrame({"x": [np.inf]})
        _, report = validate_features(df, "test")
        assert len(report.warnings) > 0
        assert "infinite" in report.warnings[0].lower() or "inf" in report.warnings[0].lower()


class TestCleanData:
    def test_clean_data_no_warnings(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
        _, report = validate_features(df, "test")
        assert len(report.warnings) == 0
        assert report.duplicate_count == 0

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        cleaned, report = validate_features(df, "empty")
        assert report.rows_input == 0
        assert report.rows_output == 0

    def test_row_count_unchanged(self):
        """Validation should not drop rows."""
        df = pd.DataFrame({"a": [1, np.inf, np.nan, -np.inf, 5]})
        cleaned, report = validate_features(df, "test")
        assert len(cleaned) == 5
        assert report.rows_input == report.rows_output
