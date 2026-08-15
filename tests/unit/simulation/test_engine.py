from __future__ import annotations

from f1_pipeline.simulation.engine import SimulationEngine
from f1_pipeline.simulation.scenario import Scenario
from f1_pipeline.simulation.schemas import SimulationResult


def test_deterministic_engine_execution():
    config = {
        "constants": {"base_vehicle_mass_kg": 800.0},
        "fuel": {"consumption_per_lap_kg": 1.5, "lap_time_effect_per_kg": 0.03},
        "track": {"base_lap_time_seconds": 90.0, "evolution_rate_per_lap": 0.0},
        "weather": {"default_track_temperature_c": 40.0},
        "tyres": {
            "compounds": {
                "SOFT": {"base_grip_multiplier": 1.0, "degradation_rate_per_lap": 0.05}
            },
            "grip_lap_time_sensitivity": 0.3
        },
        "pit_stop": {"default_loss_seconds": 20.0}
    }
    
    scenario = Scenario(
        season=2024,
        event="Test",
        session_type="R",
        driver_code="VER",
        total_laps=5,
        starting_fuel_kg=100.0,
        tyre_strategy=[{"compound": "SOFT", "start_lap": 1, "end_lap": 5}]
    )
    
    engine = SimulationEngine(config, layer3_params={})
    result = engine.run_deterministic(scenario)
    
    assert result.success
    assert result.mode == "deterministic"
    assert result.race_result is not None
    assert result.race_result.total_laps == 5
    
    laps = result.race_result.lap_results
    assert len(laps) == 5
    
    # Base lap time: 90
    # Fuel penalty lap 1 (100kg): 3.0
    # Tyre penalty lap 1 (1 lap old): 0.05
    # Lap 1 time should be around 93.05
    assert 92.0 < laps[0].lap_time < 94.0
    
    # Elapsed time should be monotonic
    for i in range(1, 5):
        assert laps[i].elapsed_time > laps[i-1].elapsed_time


def test_pit_stop_logic():
    config = {
        "track": {"base_lap_time_seconds": 90.0},
        "pit_stop": {"default_loss_seconds": 20.0}
    }
    
    scenario = Scenario(
        season=2024,
        event="Test",
        session_type="R",
        driver_code="VER",
        total_laps=3,
        tyre_strategy=[
            {"compound": "SOFT", "start_lap": 1, "end_lap": 1},
            {"compound": "HARD", "start_lap": 2, "end_lap": 3}
        ],
        pit_stops=[
            {"lap": 1, "change_compound_to": "HARD", "pit_loss_seconds": 25.0}
        ]
    )
    
    engine = SimulationEngine(config, layer3_params={})
    result = engine.run_deterministic(scenario)
    
    laps = result.race_result.lap_results
    # Lap 1 includes pit stop
    assert laps[0].pit_stop is True
    assert laps[0].pit_loss == 25.0
    assert laps[0].lap_time > 110.0 # 90 + 25 + penalties
    
    # Lap 2 is on new tyres
    assert laps[1].tyre_compound == "HARD"
    assert laps[1].tyre_age == 1
    
    # 2 stints created
    assert len(result.race_result.stint_results) == 2
    assert result.race_result.stint_results[0].compound == "SOFT"
    assert result.race_result.stint_results[1].compound == "HARD"
