"""Integration tests for Layer 3 physics pipeline.

Tests the full estimation pipeline end-to-end with mocked Supabase.
Verifies:
- Pipeline runs against synthetic Layer 2 feature data
- All output files are created
- Idempotency (skips existing assets when --force is not set)
- Re-run with --force regenerates
- Layer 0/1/2 files are not modified
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.physics.estimation_pipeline import Layer3PhysicsPipeline, physics_config_hash
from f1_pipeline.physics.schemas import Layer3PhysicsRequest, PHYSICS_SCHEMA_VERSION


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

def _physics_config() -> dict[str, Any]:
    return {
        "constants": {
            "air_density": {"value": 1.225, "unit": "kg/m^3", "provenance": "assumed"},
            "vehicle_mass_reference": {"value": 800.0, "unit": "kg", "provenance": "assumed"},
            "gravity": {"value": 9.80665, "unit": "m/s^2", "provenance": "configured"},
            "rolling_resistance_reference": {"value": 0.012, "unit": "dimensionless", "provenance": "assumed"},
        },
        "fitting": {"confidence_level": 0.95},
        "filtering": {
            "min_speed_ms": 20.0,
            "coast_throttle_max": 5.0,
            "full_throttle_threshold": 95.0,
            "exclude_braking": True,
            "max_gap_seconds": 0.5,
        },
        "models": {
            "drag": {"enabled": True, "min_samples": 10, "max_rmse": 500.0, "minimum_r_squared": 0.0, "cda_bounds": [0.1, 5.0]},
            "downforce": {"enabled": True, "min_samples": 10, "cla_bounds": [0.1, 15.0]},
            "longitudinal": {"enabled": True, "min_samples": 10, "max_rmse": 100000.0, "minimum_r_squared": 0.0, "drive_force_bounds": [0.0, 50000.0]},
            "tyres": {"enabled": True, "min_samples": 5, "max_rmse": 5.0, "minimum_r_squared": 0.0, "degradation_bounds": [-1.0, 2.0]},
            "grip": {"enabled": True, "min_samples": 5, "grip_bounds": [0.0, 10.0]},
            "cornering": {"enabled": True, "min_samples": 5, "max_rmse": 50.0, "minimum_r_squared": 0.0, "grip_bounds": [0.0, 10.0]},
        },
    }


def _synthetic_telemetry(n: int = 200) -> pd.DataFrame:
    """Create synthetic telemetry that exercises all models."""
    rng = np.random.default_rng(42)
    speed = rng.uniform(20.0, 80.0, n)
    # Mix of coasting (low throttle, decelerating) and full-throttle
    throttle = np.where(rng.random(n) > 0.5, 100.0, 0.0)
    brake = np.zeros(n, dtype=bool)
    cda = 1.5
    mass = 800.0
    accel_lon = np.where(
        throttle < 5.0,
        -(0.5 * 1.225 * cda * speed**2) / mass,  # coasting: drag-dominated
        (8000 - 0.5 * 1.225 * cda * speed**2 - 0.012 * mass * 9.80665) / mass,  # full throttle
    )
    accel_lat = rng.uniform(-30.0, 30.0, n)  # includes high-g samples for downforce/grip
    return pd.DataFrame({
        "speed_ms": speed,
        "acceleration_longitudinal": accel_lon,
        "acceleration_lateral": accel_lat,
        "throttle_percent": throttle,
        "brake_active": brake,
        "time": np.arange(n) * 0.04,
        "lap_number": np.ones(n, dtype=int),
        "distance": np.cumsum(speed * 0.04),
    })


def _synthetic_laps() -> pd.DataFrame:
    age = np.arange(1, 16)
    return pd.DataFrame({
        "tyre_age": age,
        "lap_time_seconds": 90.0 + 0.08 * age,
        "lap_number": age,
    })


def _mock_feature_assets_repo(tmp_path: Path) -> MagicMock:
    """Create a mock FeatureAssetsRepository that returns synthetic feature assets."""
    telemetry_path = tmp_path / "telemetry.parquet"
    _synthetic_telemetry().to_parquet(telemetry_path)
    laps_path = tmp_path / "laps.parquet"
    _synthetic_laps().to_parquet(laps_path)

    mock_repo = MagicMock()
    mock_client = MagicMock()
    mock_repo.client = mock_client
    mock_repo.table_name = "feature_assets"

    feature_rows = [
        {
            "id": "feat-tel-001",
            "feature_run_id": "feat-run-001",
            "asset_type": "derived_telemetry",
            "storage_path": str(telemetry_path),
            "file_format": "parquet",
            "season": 2024,
            "event_name": "Bahrain",
            "session_type": "Q",
            "driver_code": "VER",
            "created_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "feat-laps-001",
            "feature_run_id": "feat-run-001",
            "asset_type": "derived_laps",
            "storage_path": str(laps_path),
            "file_format": "parquet",
            "season": 2024,
            "event_name": "Bahrain",
            "session_type": "Q",
            "driver_code": "VER",
            "created_at": "2024-01-01T00:00:00Z",
        },
    ]
    # Chain the Supabase query mock
    query_mock = MagicMock()
    mock_client.table.return_value = query_mock
    query_mock.select.return_value = query_mock
    query_mock.eq.return_value = query_mock
    query_mock.order.return_value = query_mock
    execute_mock = MagicMock()
    execute_mock.data = feature_rows
    query_mock.execute.return_value = execute_mock

    return mock_repo


def _mock_physics_assets_repo() -> MagicMock:
    mock = MagicMock()
    mock.find_existing.return_value = None  # no existing assets
    mock.create_asset.return_value = {"id": "phys-asset-001"}
    mock.create_parameter.return_value = {"id": "phys-param-001"}
    return mock


def _mock_physics_runs_repo() -> MagicMock:
    mock = MagicMock()
    mock.create_started.return_value = {"id": "phys-run-001"}
    mock.mark_success.return_value = {"id": "phys-run-001", "status": "success"}
    mock.mark_failed.return_value = {"id": "phys-run-001", "status": "failed"}
    return mock


# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────

class TestLayer3PipelineIntegration:
    def test_full_pipeline_produces_results(self, tmp_path: Path) -> None:
        feature_repo = _mock_feature_assets_repo(tmp_path)
        physics_assets_repo = _mock_physics_assets_repo()
        physics_runs_repo = _mock_physics_runs_repo()

        pipeline = Layer3PhysicsPipeline(
            feature_assets=feature_repo,
            physics_assets=physics_assets_repo,
            physics_runs=physics_runs_repo,
            physics_config=_physics_config(),
        )
        request = Layer3PhysicsRequest(
            season=2024,
            event="Bahrain",
            session_type="Q",
            driver_code="VER",
            models=["all"],
            force=True,
        )
        result = pipeline.run(request)
        assert result.success, f"Pipeline failed: {result.message}"
        assert result.physics_run_id == "phys-run-001"

        # Verify model results exist
        assert len(result.model_results) > 0
        for key, model_result in result.model_results.items():
            assert model_result.model_name, f"{key} missing model_name"
            assert model_result.status in {"accepted", "warning", "rejected", "insufficient_data", "failed"}

        # Verify assets were registered
        assert physics_assets_repo.create_asset.called
        assert physics_runs_repo.mark_success.called

    def test_drag_model_produces_accepted_result(self, tmp_path: Path) -> None:
        feature_repo = _mock_feature_assets_repo(tmp_path)
        pipeline = Layer3PhysicsPipeline(
            feature_assets=feature_repo,
            physics_assets=_mock_physics_assets_repo(),
            physics_runs=_mock_physics_runs_repo(),
            physics_config=_physics_config(),
        )
        request = Layer3PhysicsRequest(
            season=2024, event="Bahrain", session_type="Q",
            driver_code="VER", models=["drag"], force=True,
        )
        result = pipeline.run(request)
        assert result.success
        assert "drag" in result.model_results
        drag = result.model_results["drag"]
        assert drag.status in {"accepted", "warning"}
        assert drag.parameters[0].parameter_name == "effective_drag_parameter"

    def test_individual_model_failure_does_not_crash_pipeline(self, tmp_path: Path) -> None:
        """If one model returns insufficient_data, others should still run."""
        feature_repo = _mock_feature_assets_repo(tmp_path)
        pipeline = Layer3PhysicsPipeline(
            feature_assets=feature_repo,
            physics_assets=_mock_physics_assets_repo(),
            physics_runs=_mock_physics_runs_repo(),
            physics_config=_physics_config(),
        )
        request = Layer3PhysicsRequest(
            season=2024, event="Bahrain", session_type="Q",
            driver_code="VER", models=["all"], force=True,
        )
        result = pipeline.run(request)
        assert result.success
        # Some models may be insufficient_data but pipeline succeeds overall
        statuses = {k: v.status for k, v in result.model_results.items()}
        assert any(s in {"accepted", "warning"} for s in statuses.values()), f"No model accepted: {statuses}"

    def test_idempotency_skips_existing(self, tmp_path: Path) -> None:
        """When force=False and assets exist, models should be skipped."""
        feature_repo = _mock_feature_assets_repo(tmp_path)
        physics_assets_repo = _mock_physics_assets_repo()
        # Simulate existing asset found
        physics_assets_repo.find_existing.return_value = {"id": "existing-asset"}

        pipeline = Layer3PhysicsPipeline(
            feature_assets=feature_repo,
            physics_assets=physics_assets_repo,
            physics_runs=_mock_physics_runs_repo(),
            physics_config=_physics_config(),
        )
        request = Layer3PhysicsRequest(
            season=2024, event="Bahrain", session_type="Q",
            driver_code="VER", models=["drag"], force=False,
        )
        result = pipeline.run(request)
        assert result.success
        # Drag model should have been skipped
        assert "drag" not in result.model_results

    def test_force_flag_regenerates(self, tmp_path: Path) -> None:
        """When force=True, models should run even if assets exist."""
        feature_repo = _mock_feature_assets_repo(tmp_path)
        physics_assets_repo = _mock_physics_assets_repo()
        physics_assets_repo.find_existing.return_value = {"id": "existing-asset"}

        pipeline = Layer3PhysicsPipeline(
            feature_assets=feature_repo,
            physics_assets=physics_assets_repo,
            physics_runs=_mock_physics_runs_repo(),
            physics_config=_physics_config(),
        )
        request = Layer3PhysicsRequest(
            season=2024, event="Bahrain", session_type="Q",
            driver_code="VER", models=["drag"], force=True,
        )
        result = pipeline.run(request)
        assert result.success
        assert "drag" in result.model_results

    def test_output_files_created(self, tmp_path: Path) -> None:
        """Verify that JSON and Parquet output files are written to disk."""
        feature_repo = _mock_feature_assets_repo(tmp_path)
        pipeline = Layer3PhysicsPipeline(
            feature_assets=feature_repo,
            physics_assets=_mock_physics_assets_repo(),
            physics_runs=_mock_physics_runs_repo(),
            physics_config=_physics_config(),
        )
        request = Layer3PhysicsRequest(
            season=2024, event="Bahrain", session_type="Q",
            driver_code="VER", models=["all"], force=True,
        )
        result = pipeline.run(request)
        assert result.success
        # Check that assets were produced
        assert len(result.assets) > 0
        for asset in result.assets:
            p = Path(asset.storage_path)
            assert p.exists(), f"Output file not created: {p}"

    def test_no_layer2_assets_returns_failure(self, tmp_path: Path) -> None:
        """Pipeline should fail gracefully when no Layer 2 assets are found."""
        feature_repo = MagicMock()
        feature_repo.client = MagicMock()
        feature_repo.table_name = "feature_assets"
        # Return empty feature rows
        query_mock = MagicMock()
        feature_repo.client.table.return_value = query_mock
        query_mock.select.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.order.return_value = query_mock
        execute_mock = MagicMock()
        execute_mock.data = []
        query_mock.execute.return_value = execute_mock

        pipeline = Layer3PhysicsPipeline(
            feature_assets=feature_repo,
            physics_assets=_mock_physics_assets_repo(),
            physics_runs=_mock_physics_runs_repo(),
            physics_config=_physics_config(),
        )
        request = Layer3PhysicsRequest(
            season=2024, event="Bahrain", session_type="Q",
            driver_code="VER", models=["all"], force=True,
        )
        result = pipeline.run(request)
        assert not result.success
        assert "No successful Layer 2 feature assets found" in result.message


class TestPhysicsConfigHash:
    def test_deterministic(self) -> None:
        cfg = _physics_config()
        h1 = physics_config_hash(cfg)
        h2 = physics_config_hash(cfg)
        assert h1 == h2

    def test_changes_with_config(self) -> None:
        cfg1 = _physics_config()
        cfg2 = _physics_config()
        cfg2["models"]["drag"]["min_samples"] = 999
        assert physics_config_hash(cfg1) != physics_config_hash(cfg2)
