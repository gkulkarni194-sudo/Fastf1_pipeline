from __future__ import annotations

import pytest

from f1_pipeline.simulation.environment.fuel import FuelModel
from f1_pipeline.simulation.environment.track_evolution import TrackEvolutionModel
from f1_pipeline.simulation.state import SimulationState
from f1_pipeline.simulation.tyres.degradation import TyreDegradationModel
from f1_pipeline.simulation.tyres.grip import TyreGripModel
from f1_pipeline.simulation.tyres.state import TyreState
from f1_pipeline.simulation.vehicle.dynamics import VehicleDynamicsModel
from f1_pipeline.simulation.vehicle.lateral import LateralModel
from f1_pipeline.simulation.vehicle.longitudinal import LongitudinalModel


def test_fuel_model():
    config = {"fuel": {"consumption_per_lap_kg": 1.5, "lap_time_effect_per_kg": 0.03}}
    model = FuelModel(config)
    
    assert model.fuel_mass_after_lap(100.0) == 98.5
    assert model.fuel_lap_time_effect(100.0) == 3.0


def test_tyre_degradation():
    config = {
        "tyres": {
            "compounds": {
                "SOFT": {"degradation_rate_per_lap": 0.1, "cliff_age": 10}
            }
        }
    }
    model = TyreDegradationModel(config)
    
    # Linear deg
    state = TyreState("SOFT", 5, 1.0)
    assert model.lap_time_penalty(state) == 0.5
    
    # Cliff deg
    state = TyreState("SOFT", 15, 1.0)
    # 0.1 * 15 = 1.5
    # cliff_penalty = 0.05 * (15-10)^2 = 0.05 * 25 = 1.25
    # total = 2.75
    assert pytest.approx(model.lap_time_penalty(state)) == 2.75


def test_track_evolution():
    config = {"track": {"evolution_model": "linear", "evolution_rate_per_lap": -0.01, "baseline_grip_multiplier": 1.0}}
    model = TrackEvolutionModel(config)
    
    state = SimulationState(lap=5)
    model.update_state(state)
    
    assert pytest.approx(state.track_grip_multiplier) == 0.95


def test_vehicle_dynamics():
    config = {"constants": {"air_density": {"value": 1.2}, "gravity": {"value": 9.8}, "rolling_resistance_reference": {"value": 0.01}}}
    layer3_params = {"effective_drag_parameter": 1.0, "effective_drive_force": 10000.0}
    
    dyn = VehicleDynamicsModel(config, layer3_params)
    long_model = LongitudinalModel(dyn)
    
    # Drag force: 0.5 * 1.2 * 1.0 * v^2
    # At v=50, 0.6 * 2500 = 1500
    assert long_model.drag_force(50.0) == 1500.0
    
    # Rolling resistance: 0.01 * 800 * 9.8 = 78.4
    assert pytest.approx(long_model.rolling_resistance(800.0)) == 78.4
