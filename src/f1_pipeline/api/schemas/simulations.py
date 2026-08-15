"""Simulation schemas."""
from __future__ import annotations

from pydantic import BaseModel

from f1_pipeline.simulation.scenario import Scenario


class SimulationCreateRequest(BaseModel):
    season: int
    event: str
    session: str
    driver: str
    scenario: Scenario
    # Optional parameters to override defaults
    seed: int = 42
    monte_carlo: bool = False
    iterations: int = 100


class JobQueuedResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None


class SimulationResultResponse(BaseModel):
    simulation_id: str
    success: bool
    total_race_time: float | None = None
    total_laps: int | None = None
    mean_race_time: float | None = None
    std_race_time: float | None = None
    stints: list[dict] = []
