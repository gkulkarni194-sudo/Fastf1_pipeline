"""Optimization schemas."""
from __future__ import annotations

from pydantic import BaseModel

from f1_pipeline.strategy.schemas import Strategy


class OptimizationConstraints(BaseModel):
    minimum_stops: int = 1
    maximum_stops: int = 3
    minimum_stint_laps: int = 5
    available_compounds: list[str] = ["SOFT", "MEDIUM", "HARD"]


class OptimizationCreateRequest(BaseModel):
    season: int
    event: str
    session: str
    driver: str
    
    algorithm: str = "exhaustive"
    objective: str = "race_time"
    monte_carlo: bool = False
    iterations: int = 100
    seed: int = 42
    
    constraints: OptimizationConstraints = OptimizationConstraints()


class OptimizationResultResponse(BaseModel):
    optimization_id: str
    best_strategy: Strategy | None
    best_score: float | None
    best_race_time: float | None
    strategies_evaluated: int
    strategies_valid: int
    algorithm: str
    objective: str
