"""Tests for normalization schemas."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from f1_pipeline.normalization.schemas import (
    CANONICAL_SCHEMA_VERSION,
    CanonicalAssetResult,
    DuplicateReport,
    Layer1NormalizationRequest,
    Layer1NormalizationResult,
    QualityReport,
)


class TestCanonicalSchemaVersion:
    def test_version_is_string(self):
        assert isinstance(CANONICAL_SCHEMA_VERSION, str)

    def test_version_is_1_0(self):
        assert CANONICAL_SCHEMA_VERSION == "1.0"


class TestLayer1NormalizationRequest:
    def test_valid_request(self):
        req = Layer1NormalizationRequest(
            season=2024, event="Bahrain", session_type="Q", driver_code="VER",
        )
        assert req.season == 2024
        assert req.force is False
        assert req.asset_types == ["laps", "weather", "telemetry"]

    def test_force_flag(self):
        req = Layer1NormalizationRequest(
            season=2024, event="Bahrain", session_type="Q", force=True,
        )
        assert req.force is True

    def test_invalid_season(self):
        with pytest.raises(ValidationError):
            Layer1NormalizationRequest(season=1900, event="X", session_type="Q")

    def test_custom_asset_types(self):
        req = Layer1NormalizationRequest(
            season=2024, event="Bahrain", session_type="Q",
            asset_types=["laps"],
        )
        assert req.asset_types == ["laps"]


class TestQualityReport:
    def test_defaults(self):
        qr = QualityReport(asset_type="laps")
        assert qr.valid is True
        assert qr.rows == 0
        assert qr.warnings == []
        assert qr.errors == []

    def test_with_errors(self):
        qr = QualityReport(asset_type="laps", valid=False, errors=["Missing column"])
        assert qr.valid is False


class TestDuplicateReport:
    def test_values(self):
        dr = DuplicateReport(
            asset_type="laps", rows_before=100, duplicates_found=5, rows_after=95,
        )
        assert dr.duplicates_found == 5


class TestCanonicalAssetResult:
    def test_schema_version_default(self):
        result = CanonicalAssetResult(
            asset_type="laps", season=2024, event="Bahrain",
            session_type="Q", storage_path="test.parquet",
            checksum="a" * 64,
        )
        assert result.schema_version == CANONICAL_SCHEMA_VERSION
