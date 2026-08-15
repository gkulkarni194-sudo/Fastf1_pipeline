"""Physics schemas."""
from __future__ import annotations

from pydantic import BaseModel


class PhysicsRunResponse(BaseModel):
    id: str
    season: int
    event: str
    session: str
    driver: str
    status: str
    algorithm: str
    created_at: str
    completed_at: str | None


class PhysicsParametersResponse(BaseModel):
    aero: dict | None
    tyres: dict | None
    longitudinal: dict | None
    cornering: dict | None
    version: str
