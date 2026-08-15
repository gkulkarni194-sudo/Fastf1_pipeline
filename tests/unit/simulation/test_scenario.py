from __future__ import annotations

import pytest
from pydantic import ValidationError

from f1_pipeline.simulation.scenario import Scenario


def test_valid_scenario():
    data = {
        "season": 2024,
        "event": "Bahrain Grand Prix",
        "session_type": "R",
        "driver_code": "VER",
        "total_laps": 57,
        "starting_fuel_kg": 110.0,
        "tyre_strategy": [
            {"compound": "SOFT", "start_lap": 1, "end_lap": 15},
            {"compound": "HARD", "start_lap": 16, "end_lap": 57},
        ],
        "pit_stops": [
            {"lap": 15, "change_compound_to": "HARD"}
        ]
    }
    
    scenario = Scenario.model_validate(data)
    assert scenario.season == 2024
    
    # Hash should be deterministic
    hash1 = scenario.scenario_hash()
    hash2 = scenario.scenario_hash()
    assert hash1 == hash2
    
    warnings = scenario.validate_scenario()
    assert len(warnings) == 0


def test_scenario_validation_warnings():
    data = {
        "season": 2024,
        "event": "Bahrain Grand Prix",
        "session_type": "R",
        "driver_code": "VER",
        "total_laps": 57,
        "tyre_strategy": [
            {"compound": "SOFT", "start_lap": 1, "end_lap": 15},
            {"compound": "HARD", "start_lap": 20, "end_lap": 57}, # Gap 16-19
        ],
        "pit_stops": [] # Missing pit stop for transition
    }
    
    scenario = Scenario.model_validate(data)
    warnings = scenario.validate_scenario()
    
    assert len(warnings) == 2
    assert any("gap or overlap" in w for w in warnings)
    assert any("no pit stop" in w for w in warnings)
