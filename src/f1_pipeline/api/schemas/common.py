"""Common API schemas."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    page: int
    page_size: int
    total_count: int | None = None
    has_next: bool


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list | dict | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: str


class HealthDependenciesResponse(BaseModel):
    database: str
    storage: str
    pipeline: str
