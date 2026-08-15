"""Simulation validation routines."""
from __future__ import annotations

from f1_pipeline.simulation.schemas import RaceResult
from f1_pipeline.simulation.state import SimulationState


class ValidationError(Exception):
    pass


def validate_state(state: SimulationState) -> None:
    """Validate that the simulation state is physically plausible."""
    if state.lap < 0:
        raise ValidationError(f"Invalid lap number: {state.lap}")
    if state.elapsed_time_s < 0:
        raise ValidationError(f"Invalid elapsed time: {state.elapsed_time_s}")
    if state.fuel_mass_kg < 0:
        raise ValidationError(f"Negative fuel mass: {state.fuel_mass_kg}")
    if state.vehicle_mass_kg <= 0:
        raise ValidationError(f"Invalid vehicle mass: {state.vehicle_mass_kg}")
    if state.tyre_age < 0:
        raise ValidationError(f"Negative tyre age: {state.tyre_age}")


def validate_results(result: RaceResult) -> list[str]:
    """Validate simulation results for consistency."""
    warnings = []
    
    if result.total_laps != len(result.lap_results):
        warnings.append(f"Lap count mismatch: {result.total_laps} != {len(result.lap_results)}")
        
    for lap in result.lap_results:
        if lap.lap_time <= 0:
            warnings.append(f"Non-positive lap time on lap {lap.lap_number}: {lap.lap_time}")
            
    # Check elapsed time monotonicity
    current_elapsed = 0.0
    for lap in result.lap_results:
        if lap.elapsed_time < current_elapsed:
            warnings.append(f"Non-monotonic elapsed time on lap {lap.lap_number}")
        current_elapsed = lap.elapsed_time
        
    return warnings
