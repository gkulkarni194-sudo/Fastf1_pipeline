"""Tests for missing_values module."""
from __future__ import annotations

import numpy as np
import pandas as pd

from f1_pipeline.normalization.missing_values import (
    normalize_missing_values,
    report_missing_values,
)


class TestNormalizeMissingValues:
    def test_empty_string_becomes_nan(self):
        df = pd.DataFrame({"col": ["hello", "", "world"]})
        out = normalize_missing_values(df)
        assert out["col"].iloc[0] == "hello"
        assert out["col"].iloc[1] is None
        assert out["col"].iloc[2] == "world"

    def test_whitespace_only_becomes_nan(self):
        df = pd.DataFrame({"col": ["   ", "ok"]})
        out = normalize_missing_values(df)
        assert out["col"].iloc[0] is None
        assert out["col"].iloc[1] == "ok"

    def test_string_none_sentinel(self):
        df = pd.DataFrame({"col": ["None", "null", "NaN", "valid"]})
        out = normalize_missing_values(df)
        assert out["col"].iloc[0] is None
        assert out["col"].iloc[1] is None
        assert out["col"].iloc[2] is None
        assert out["col"].iloc[3] == "valid"

    def test_numeric_columns_untouched(self):
        df = pd.DataFrame({"num": [1.0, np.nan, 3.0]})
        out = normalize_missing_values(df)
        assert out["num"].iloc[0] == 1.0
        assert pd.isna(out["num"].iloc[1])
        assert out["num"].iloc[2] == 3.0

    def test_no_interpolation(self):
        df = pd.DataFrame({"val": [1.0, np.nan, 3.0]})
        out = normalize_missing_values(df)
        assert pd.isna(out["val"].iloc[1])  # NOT interpolated to 2.0

    def test_no_forward_fill(self):
        df = pd.DataFrame({"val": [1.0, np.nan, np.nan, 4.0]})
        out = normalize_missing_values(df)
        assert pd.isna(out["val"].iloc[1])
        assert pd.isna(out["val"].iloc[2])

    def test_returns_copy(self):
        df = pd.DataFrame({"col": ["a"]})
        out = normalize_missing_values(df)
        assert out is not df


class TestReportMissingValues:
    def test_reports_missing_counts(self):
        df = pd.DataFrame({
            "a": [1.0, np.nan, 3.0],
            "b": ["x", "y", "z"],
        })
        report = report_missing_values(df)
        assert report == {"a": 1}

    def test_empty_report_when_no_missing(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        report = report_missing_values(df)
        assert report == {}
