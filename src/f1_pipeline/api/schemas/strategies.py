"""Strategy comparison schemas."""
from __future__ import annotations

from pydantic import BaseModel


class StrategyCompareRequest(BaseModel):
    strategy_hashes: list[str]
    # Optionally override context
    optimization_run_id: str | None = None


class StrategyMetrics(BaseModel):
    strategy_hash: str
    objective_score: float | None
    race_time: float | None
    pit_stops: int
    valid: bool


class StrategyCompareResponse(BaseModel):
    comparisons: list[StrategyMetrics]
