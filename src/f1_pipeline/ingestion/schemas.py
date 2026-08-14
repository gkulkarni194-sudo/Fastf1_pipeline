from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


SUPPORTED_SESSION_TYPES = {"FP1", "FP2", "FP3", "Q", "SQ", "S", "R"}


class Layer0IngestionRequest(BaseModel):
    season: int = Field(ge=1950)
    event: str = Field(min_length=1, max_length=255)
    session_type: str = Field(min_length=1, max_length=32)
    driver_code: str | None = Field(default=None, max_length=8)
    config_hash: str | None = Field(default=None, min_length=64, max_length=64)
    code_version: str | None = Field(default=None, max_length=128)
    force: bool = False

    @field_validator("session_type")
    @classmethod
    def normalize_session_type(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in SUPPORTED_SESSION_TYPES:
            supported = ", ".join(sorted(SUPPORTED_SESSION_TYPES))
            raise ValueError(f"Unsupported session_type '{value}'. Supported values: {supported}")
        return normalized

    @field_validator("driver_code")
    @classmethod
    def normalize_driver_code(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class RawAssetResult(BaseModel):
    source: str = Field(min_length=1, max_length=64)
    asset_type: str = Field(min_length=1, max_length=64)
    season: int = Field(ge=1950)
    event: str = Field(min_length=1, max_length=255)
    session_type: str = Field(min_length=1, max_length=32)
    driver_code: str | None = Field(default=None, max_length=8)
    lap_number: int | None = Field(default=None, ge=1)
    storage_path: str = Field(min_length=1)
    file_format: str = Field(min_length=1, max_length=32)
    checksum: str = Field(min_length=64, max_length=64)
    row_count: int | None = Field(default=None, ge=0)


class Layer0IngestionResult(BaseModel):
    season: int
    event: str
    session_type: str
    driver_code: str | None = None
    ingestion_run_id: str | None = None
    assets: list[RawAssetResult] = Field(default_factory=list)
    success: bool
    message: str


class QualityReport(BaseModel):
    asset_type: str
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
