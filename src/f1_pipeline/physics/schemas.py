from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


PHYSICS_SCHEMA_VERSION = "1.0"
ModelStatus = Literal["accepted", "warning", "rejected", "insufficient_data", "failed"]


class IdentifiabilityReport(BaseModel):
    identifiable_parameters: list[str] = Field(default_factory=list)
    non_identifiable_parameters: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class PhysicsParameterEstimate(BaseModel):
    parameter_name: str
    value: float | None = None
    unit: str
    standard_error: float | None = None
    confidence_interval_low: float | None = None
    confidence_interval_high: float | None = None
    sample_count: int = 0
    model_name: str
    model_version: str
    status: ModelStatus
    provenance: Literal["observed", "configured", "assumed", "estimated"] = "estimated"


class PhysicsDiagnostics(BaseModel):
    rmse: float | None = None
    mae: float | None = None
    r_squared: float | None = None
    sample_count: int = 0
    residual_mean: float | None = None
    residual_std: float | None = None
    convergence_status: str = "not_run"
    rows_input: int = 0
    rows_used: int = 0
    rows_excluded: int = 0
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class PhysicsModelResult(BaseModel):
    model_name: str
    model_version: str
    parameters: list[PhysicsParameterEstimate] = Field(default_factory=list)
    diagnostics: PhysicsDiagnostics = Field(default_factory=PhysicsDiagnostics)
    identifiability: IdentifiabilityReport = Field(default_factory=IdentifiabilityReport)
    status: ModelStatus
    predictions: list[dict[str, Any]] = Field(default_factory=list)
    residuals: list[dict[str, Any]] = Field(default_factory=list)


class Layer3PhysicsRequest(BaseModel):
    season: int = Field(ge=1950)
    event: str = Field(min_length=1, max_length=255)
    session_type: str = Field(min_length=1, max_length=32)
    driver_code: str | None = Field(default=None, max_length=8)
    models: list[str] = Field(default_factory=lambda: ["all"])
    force: bool = False
    config_hash: str | None = Field(default=None, max_length=64)
    code_version: str | None = Field(default=None, max_length=128)


class PhysicsAssetResult(BaseModel):
    source_feature_asset_id: str | None = None
    asset_type: str
    season: int
    event: str
    session_type: str
    driver_code: str | None = None
    storage_path: str
    file_format: str
    checksum: str
    row_count: int | None = None
    schema_version: str = PHYSICS_SCHEMA_VERSION


class Layer3PhysicsResult(BaseModel):
    physics_run_id: str | None = None
    source_feature_run_id: str | None = None
    assets: list[PhysicsAssetResult] = Field(default_factory=list)
    model_results: dict[str, PhysicsModelResult] = Field(default_factory=dict)
    skipped_assets: list[str] = Field(default_factory=list)
    success: bool
    message: str
