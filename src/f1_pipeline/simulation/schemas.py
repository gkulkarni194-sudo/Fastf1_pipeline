"""Layer 4 simulation schemas.

All result types used by the simulation engine, scenario runner,
and Monte Carlo modules.  Every schema is Pydantic-serializable.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SIMULATION_SCHEMA_VERSION = "1.0"

SimulationMode = Literal["deterministic", "monte_carlo"]
CompoundName = Literal["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]


# ── Fallback tracking ─────────────────────────────────────────

class FallbackRecord(BaseModel):
    """Records when a configured fallback was used instead of a Layer 3 estimate."""
    parameter: str
    source: Literal["layer3_estimate", "configured_fallback", "simplified_model", "unavailable"]
    value: float | None = None
    reason: str = ""


# ── Lap / stint / race results ─────────────────────────────────

class LapResult(BaseModel):
    lap_number: int
    lap_time: float
    elapsed_time: float
    fuel_used: float
    fuel_remaining: float
    tyre_age: int
    tyre_compound: str
    tyre_grip: float
    vehicle_mass: float
    pit_stop: bool = False
    pit_loss: float = 0.0
    max_speed: float | None = None
    average_speed: float | None = None
    sector_times: list[float] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StintResult(BaseModel):
    stint_number: int
    starting_lap: int
    ending_lap: int
    compound: str
    lap_times: list[float]
    average_lap_time: float
    total_time: float
    degradation_total: float
    fuel_used: float
    tyre_age_start: int
    tyre_age_end: int


class PitEvent(BaseModel):
    lap: int
    pit_loss_seconds: float
    compound_before: str
    compound_after: str
    tyre_age_at_stop: int
    fuel_remaining: float


class RaceResult(BaseModel):
    total_race_time: float
    total_laps: int
    lap_results: list[LapResult]
    stint_results: list[StintResult]
    pit_events: list[PitEvent]
    total_fuel_used: float
    total_pit_time: float
    warnings: list[str] = Field(default_factory=list)


class MonteCarloIteration(BaseModel):
    iteration: int
    seed: int
    sampled_parameters: dict[str, float]
    total_race_time: float
    lap_times: list[float]
    warnings: list[str] = Field(default_factory=list)


class MonteCarloSummary(BaseModel):
    iterations: int
    mean_race_time: float
    median_race_time: float
    std_race_time: float
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float
    mean_lap_times: list[float]
    std_lap_times: list[float]


class MonteCarloResult(BaseModel):
    summary: MonteCarloSummary
    iterations: list[MonteCarloIteration] = Field(default_factory=list)


class SimulationAssetRecord(BaseModel):
    asset_type: str
    storage_path: str
    file_format: str
    checksum: str
    row_count: int | None = None


class SimulationResult(BaseModel):
    success: bool
    message: str = ""
    simulation_run_id: str | None = None
    scenario_id: str | None = None
    scenario_hash: str | None = None
    mode: SimulationMode = "deterministic"
    race_result: RaceResult | None = None
    monte_carlo_result: MonteCarloResult | None = None
    fallbacks: list[FallbackRecord] = Field(default_factory=list)
    assets: list[SimulationAssetRecord] = Field(default_factory=list)
    model_results: dict[str, Any] = Field(default_factory=dict)
