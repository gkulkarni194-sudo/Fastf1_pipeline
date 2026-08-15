"""Core Simulation Engine."""
from __future__ import annotations

import logging
from typing import Any

from f1_pipeline.simulation.environment.fuel import FuelModel
from f1_pipeline.simulation.environment.track_evolution import TrackEvolutionModel
from f1_pipeline.simulation.environment.weather import WeatherModel
from f1_pipeline.simulation.results import build_race_result
from f1_pipeline.simulation.scenario import Scenario
from f1_pipeline.simulation.schemas import LapResult, PitEvent, RaceResult, SimulationResult
from f1_pipeline.simulation.state import SimulationState
from f1_pipeline.simulation.track.model import EmpiricalTrackModel
from f1_pipeline.simulation.tyres.degradation import TyreDegradationModel
from f1_pipeline.simulation.tyres.grip import TyreGripModel
from f1_pipeline.simulation.validation import validate_state, validate_results

logger = logging.getLogger(__name__)


class SimulationEngine:
    """The core engine that runs a race simulation."""

    def __init__(self, config: dict[str, Any], layer3_params: dict[str, Any], layer2_features: dict[str, Any] | None = None):
        self.config = config
        self.layer3_params = layer3_params
        self.layer2_features = layer2_features or {}
        
        # Initialize models
        self.fuel_model = FuelModel(config)
        self.weather_model = WeatherModel(config)
        self.track_model = EmpiricalTrackModel(config, layer2_features)
        self.track_evolution = TrackEvolutionModel(config)
        self.tyre_grip = TyreGripModel(config, layer3_params)
        self.tyre_deg = TyreDegradationModel(config, layer3_params)
        
        # Collect fallbacks
        self.fallbacks = []
        self.fallbacks.extend(self.track_model.fallbacks)
        self.fallbacks.extend(self.tyre_grip.fallbacks)
        self.fallbacks.extend(self.tyre_deg.fallbacks)

    def run_deterministic(self, scenario: Scenario, seed: int = 42) -> SimulationResult:
        """Run a single deterministic race simulation based on the scenario."""
        warnings: list[str] = scenario.validate_scenario()
        
        # Initialize state
        state = SimulationState()
        
        # Fuel
        state.fuel_mass_kg = scenario.starting_fuel_kg or float(self.config.get("fuel", {}).get("starting_fuel_kg", 100.0))
        base_vehicle_mass = float(self.config.get("constants", {}).get("base_vehicle_mass_kg", 798.0))
        state.vehicle_mass_kg = base_vehicle_mass + state.fuel_mass_kg
        
        # Weather
        self.weather_model.initialize_state(state, scenario.weather)
        
        # Track
        self.track_evolution.initialize_state(state)
        
        # Tyres
        if not scenario.tyre_strategy:
            return SimulationResult(success=False, message="No tyre strategy provided in scenario.")
            
        initial_stint = scenario.tyre_strategy[0]
        state.tyre_compound = initial_stint.compound
        state.tyre_age = 0
        state.tyre_grip_multiplier = self.tyre_grip.get_base_grip(state.tyre_compound)
        
        lap_results: list[LapResult] = []
        pit_events: list[PitEvent] = []
        
        # Build pit stop lookup
        pit_stops_by_lap = {stop.lap: stop for stop in scenario.pit_stops}
        strategy_by_lap = {stint.start_lap: stint for stint in scenario.tyre_strategy}
        
        # Main simulation loop
        for lap_num in range(1, scenario.total_laps + 1):
            state.lap = lap_num
            
            # 1. Update compound if dictated by strategy (simulating the tyre change happening before the lap starts)
            # Typically a pit stop at end of lap N changes compound for lap N+1
            if lap_num in strategy_by_lap and lap_num > 1:
                stint = strategy_by_lap[lap_num]
                state.tyre_compound = stint.compound
                state.tyre_age = 0
                state.tyre_grip_multiplier = self.tyre_grip.get_base_grip(state.tyre_compound)
                
            state.tyre_age += 1
            
            # 2. Check for pit stop on THIS lap
            pit_stop = pit_stops_by_lap.get(lap_num)
            state.pit_status = pit_stop is not None
            
            # 3. Simulate Lap Time (Empirical Model)
            base_time = self.track_model.base_lap_time
            
            # Tyre effects
            from f1_pipeline.simulation.tyres.state import TyreState
            tyre_state = TyreState(
                compound=state.tyre_compound,
                age=state.tyre_age,
                grip_multiplier=state.tyre_grip_multiplier
            )
            from_base_grip = self.tyre_grip.grip_lap_time_effect(tyre_state)  # Multiplier
            from_deg = self.tyre_deg.lap_time_penalty(tyre_state)             # Additive penalty
            
            # Fuel effect
            from_fuel = self.fuel_model.fuel_lap_time_effect(state.fuel_mass_kg) # Additive penalty
            
            # Weather & Track evolution
            weather_mult = self.weather_model.weather_lap_time_adjustment(state, base_time)
            track_evol_mult = state.track_grip_multiplier # Lower is faster
            
            # Calculate final lap time
            # base_time * (grip_mult * weather_mult * track_evol_mult) + deg_penalty + fuel_penalty
            # This is a simplified empirical combination.
            
            # Re-center multipliers around 1.0
            combined_mult = 1.0 + (from_base_grip - 1.0) + (weather_mult - 1.0) + (track_evol_mult - 1.0)
            
            lap_time = base_time * combined_mult + from_deg + from_fuel
            
            # Add pit loss
            pit_loss = 0.0
            if state.pit_status and pit_stop:
                pit_loss = pit_stop.pit_loss_seconds or float(self.config.get("pit_stop", {}).get("default_loss_seconds", 22.0))
                lap_time += pit_loss
                
            state.elapsed_time_s += lap_time
            
            # 4. Consume Fuel
            fuel_before = state.fuel_mass_kg
            state.fuel_mass_kg = self.fuel_model.fuel_mass_after_lap(state.fuel_mass_kg, stochastic=False)
            fuel_used = fuel_before - state.fuel_mass_kg
            state.vehicle_mass_kg = base_vehicle_mass + state.fuel_mass_kg
            
            # 5. Validate State
            validate_state(state)
            
            # 6. Record Lap
            lap_result = LapResult(
                lap_number=lap_num,
                lap_time=lap_time,
                elapsed_time=state.elapsed_time_s,
                fuel_used=fuel_used,
                fuel_remaining=state.fuel_mass_kg,
                tyre_age=state.tyre_age,
                tyre_compound=state.tyre_compound,
                tyre_grip=state.tyre_grip_multiplier,
                vehicle_mass=state.vehicle_mass_kg,
                pit_stop=state.pit_status,
                pit_loss=pit_loss
            )
            lap_results.append(lap_result)
            
            # 7. Record Pit Event
            if state.pit_status and pit_stop:
                next_compound = pit_stop.change_compound_to
                if not next_compound and (lap_num + 1) in strategy_by_lap:
                    next_compound = strategy_by_lap[lap_num + 1].compound
                    
                pit_events.append(PitEvent(
                    lap=lap_num,
                    pit_loss_seconds=pit_loss,
                    compound_before=state.tyre_compound,
                    compound_after=next_compound or "UNKNOWN",
                    tyre_age_at_stop=state.tyre_age,
                    fuel_remaining=state.fuel_mass_kg
                ))
            
            # 8. Update Environment for next lap
            self.track_evolution.update_state(state)
            self.weather_model.update_state(state)

        # Build final race result
        race_result = build_race_result(lap_results, pit_events, warnings)
        
        # Validate final results
        result_warnings = validate_results(race_result)
        race_result.warnings.extend(result_warnings)
        
        return SimulationResult(
            success=True,
            mode="deterministic",
            race_result=race_result,
            fallbacks=self.fallbacks
        )
