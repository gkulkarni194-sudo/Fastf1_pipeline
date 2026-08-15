"""Simulation result construction."""
from __future__ import annotations

from f1_pipeline.simulation.schemas import LapResult, PitEvent, RaceResult, StintResult


def aggregate_stints(lap_results: list[LapResult], pit_events: list[PitEvent]) -> list[StintResult]:
    """Aggregate lap results into stint results."""
    stints = []
    
    if not lap_results:
        return stints
        
    current_stint_laps = []
    stint_number = 1
    
    for lap in lap_results:
        current_stint_laps.append(lap)
        
        # If this lap had a pit stop (and isn't the last lap), end the stint
        if lap.pit_stop and lap.lap_number < len(lap_results):
            stints.append(_create_stint(stint_number, current_stint_laps))
            current_stint_laps = []
            stint_number += 1
            
    # Add final stint
    if current_stint_laps:
        stints.append(_create_stint(stint_number, current_stint_laps))
        
    return stints


def _create_stint(stint_number: int, laps: list[LapResult]) -> StintResult:
    lap_times = [l.lap_time for l in laps]
    return StintResult(
        stint_number=stint_number,
        starting_lap=laps[0].lap_number,
        ending_lap=laps[-1].lap_number,
        compound=laps[0].tyre_compound,
        lap_times=lap_times,
        average_lap_time=sum(lap_times) / len(lap_times) if lap_times else 0.0,
        total_time=sum(lap_times),
        degradation_total=laps[-1].lap_time - laps[0].lap_time if len(laps) > 1 else 0.0,
        fuel_used=sum(l.fuel_used for l in laps),
        tyre_age_start=laps[0].tyre_age,
        tyre_age_end=laps[-1].tyre_age,
    )


def build_race_result(lap_results: list[LapResult], pit_events: list[PitEvent], warnings: list[str]) -> RaceResult:
    """Build a complete RaceResult from laps and pit events."""
    stints = aggregate_stints(lap_results, pit_events)
    
    total_time = sum(l.lap_time for l in lap_results)
    total_fuel = sum(l.fuel_used for l in lap_results)
    total_pit = sum(p.pit_loss_seconds for p in pit_events)
    
    return RaceResult(
        total_race_time=total_time,
        total_laps=len(lap_results),
        lap_results=lap_results,
        stint_results=stints,
        pit_events=pit_events,
        total_fuel_used=total_fuel,
        total_pit_time=total_pit,
        warnings=warnings
    )
