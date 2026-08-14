from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Schema version — bump this when the canonical column set changes.
# Stored in canonical_assets for reproducibility.
# ---------------------------------------------------------------------------
CANONICAL_SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Request / result models
# ---------------------------------------------------------------------------
class Layer1NormalizationRequest(BaseModel):
    season: int = Field(ge=1950)
    event: str = Field(min_length=1, max_length=255)
    session_type: str = Field(min_length=1, max_length=32)
    driver_code: str | None = Field(default=None, max_length=8)
    asset_types: list[str] = Field(default_factory=lambda: ["laps", "weather", "telemetry"])
    force: bool = False
    config_hash: str | None = Field(default=None, max_length=64)
    code_version: str | None = Field(default=None, max_length=128)


class CanonicalAssetResult(BaseModel):
    source_asset_id: str | None = None
    asset_type: str
    season: int
    event: str
    session_type: str
    driver_code: str | None = None
    storage_path: str
    file_format: str = "parquet"
    checksum: str
    row_count: int | None = None
    schema_version: str = CANONICAL_SCHEMA_VERSION


class QualityReport(BaseModel):
    asset_type: str
    valid: bool = True
    rows: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    missing_columns: list[str] = Field(default_factory=list)


class DuplicateReport(BaseModel):
    asset_type: str
    rows_before: int = 0
    duplicates_found: int = 0
    rows_after: int = 0


class Layer1NormalizationResult(BaseModel):
    normalization_run_id: str | None = None
    source_ingestion_run_id: str | None = None
    assets: list[CanonicalAssetResult] = Field(default_factory=list)
    skipped_assets: list[str] = Field(default_factory=list)
    quality_reports: list[QualityReport] = Field(default_factory=list)
    duplicate_reports: list[DuplicateReport] = Field(default_factory=list)
    success: bool
    message: str
