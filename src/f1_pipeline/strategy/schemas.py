"""Schemas for strategy optimization."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StintSpec(BaseModel):
    compound: str
    start_lap: int
    end_lap: int
    

class PitSpec(BaseModel):
    lap: int
    pit_loss_seconds: float | None = None
    change_compound_to: str | None = None


class Strategy(BaseModel):
    driver_code: str
    stints: list[StintSpec] = Field(default_factory=list)
    pit_stops: list[PitSpec] = Field(default_factory=list)


class ConstraintResult(BaseModel):
    valid: bool
    violations: list[str] = Field(default_factory=list)


class StrategyEvaluation(BaseModel):
    strategy_hash: str
    strategy: Strategy
    constraint_status: str
    
    # These fields are populated after simulation
    race_time: float | None = None
    mean_race_time: float | None = None
    std_race_time: float | None = None
    p05_race_time: float | None = None
    p50_race_time: float | None = None
    p95_race_time: float | None = None
    objective_score: float | None = None
    
    risk_metrics: dict[str, float] = Field(default_factory=dict)
    
    # Internal representation of simulation results if caching enables it
    # Not serialized for DB, but useful during runtime
    simulated_laps: int | None = None


class OptimizationResult(BaseModel):
    optimization_run_id: str
    best_strategy: Strategy | None = None
    best_score: float | None = None
    best_race_time: float | None = None
    
    strategies_evaluated: int = 0
    strategies_valid: int = 0
    strategies_rejected: int = 0
    
    algorithm: str
    objective: str
    pareto_frontier_size: int = 0
    status: str
