from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Schema version — bump this when the derived features column set changes.
# Stored in feature_assets for reproducibility.
# ---------------------------------------------------------------------------
FEATURE_SCHEMA_VERSION = "1.0"


class Layer2FeatureRequest(BaseModel):
    season: int = Field(ge=1950)
    event: str = Field(min_length=1, max_length=255)
    session_type: str = Field(min_length=1, max_length=32)
    driver_code: str | None = Field(default=None, max_length=8)
    feature_sets: list[str] = Field(default_factory=lambda: ["telemetry", "laps", "corners", "stints"])
    force: bool = False
    config_hash: str | None = Field(default=None, max_length=64)
    code_version: str | None = Field(default=None, max_length=128)


class FeatureAssetResult(BaseModel):
    source_asset_id: str
    asset_type: str
    season: int
    event: str
    session_type: str
    driver_code: str | None = None
    storage_path: str
    file_format: str = "parquet"
    checksum: str
    row_count: int | None = None
    schema_version: str = FEATURE_SCHEMA_VERSION


class QualityReport(BaseModel):
    asset_type: str
    valid: bool = True
    rows_input: int = 0
    rows_output: int = 0
    features_created: list[str] = Field(default_factory=list)
    missing_feature_counts: dict[str, int] = Field(default_factory=dict)
    invalid_values_count: dict[str, int] = Field(default_factory=dict)
    duplicate_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class Layer2FeatureResult(BaseModel):
    feature_run_id: str | None = None
    source_normalization_run_id: str | None = None
    assets: list[FeatureAssetResult] = Field(default_factory=list)
    skipped_assets: list[str] = Field(default_factory=list)
    quality_reports: list[QualityReport] = Field(default_factory=list)
    success: bool
    message: str
