from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from f1_pipeline.core.config import RuntimeConfig
from f1_pipeline.core.paths import ProjectPaths
from f1_pipeline.simulation.pipeline import Layer4SimulationPipeline
from f1_pipeline.simulation.scenario import Scenario


@pytest.fixture
def mock_paths(tmp_path):
    paths = ProjectPaths.from_root(tmp_path)
    paths.ensure_directories()
    return paths


@pytest.fixture
def mock_config():
    return RuntimeConfig({
        "simulation": {
            "fuel": {"consumption_per_lap_kg": 1.5, "lap_time_effect_per_kg": 0.035},
            "track": {"base_lap_time_seconds": 90.0},
            "tyres": {"compounds": {"SOFT": {"base_grip_multiplier": 1.0, "degradation_rate_per_lap": 0.05}}},
        }
    })


@patch("f1_pipeline.simulation.pipeline.PhysicsRunsRepository")
@patch("f1_pipeline.simulation.pipeline.SimulationRunsRepository")
@patch("f1_pipeline.simulation.pipeline.SimulationAssetsRepository")
def test_simulation_pipeline_execution(
    mock_assets_repo, mock_runs_repo, mock_physics_repo,
    mock_paths, mock_config
):
    # Setup mock layer 3 outputs
    layer3_dir = mock_paths.processed / "physics" / "2024" / "test" / "r" / "VER"
    layer3_dir.mkdir(parents=True)
    with (layer3_dir / "parameters.json").open("w") as f:
        json.dump({"effective_drag_parameter": 1.5, "effective_downforce_parameter": 4.0}, f)
        
    scenario = Scenario(
        season=2024,
        event="Test",
        session_type="R",
        driver_code="VER",
        total_laps=10,
        tyre_strategy=[{"compound": "SOFT", "start_lap": 1, "end_lap": 10}]
    )
    
    # Setup mocks
    mock_assets = mock_assets_repo.return_value
    mock_assets.find_scenario_by_hash.return_value = None
    mock_assets.create_scenario.return_value = "scen-id"
    
    mock_runs = mock_runs_repo.return_value
    mock_runs.create_started.return_value = "run-id"
    
    pipeline = Layer4SimulationPipeline(mock_config, mock_paths)
    
    result = pipeline.execute(scenario)
    
    assert result.success
    assert result.mode == "deterministic"
    assert result.race_result.total_laps == 10
    
    # Verify outputs saved
    out_dir = mock_paths.processed / "simulations" / "2024" / "test" / "r" / "VER"
    assert (out_dir / "simulation_result.json").exists()
    
    # Verify DB calls
    mock_runs.create_started.assert_called_once()
    mock_runs.mark_success.assert_called_once()
    mock_assets.create_asset.assert_called_once()
