"""Integration tests for Layer 2 feature pipeline."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.features.feature_pipeline import Layer2Pipeline
from f1_pipeline.features.schemas import Layer2FeatureRequest


@pytest.fixture
def mock_canonical_repo():
    repo = MagicMock()
    # Mock discover method output
    def _mock_execute():
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "canon-lap-id-1",
                "normalization_run_id": "norm-run-id-1",
                "season": 2024,
                "event_name": "Bahrain",
                "session_type": "Q",
                "driver_code": "VER",
                "asset_type": "laps",
                "storage_path": "data/interim/canonical/2024/bahrain/Q/laps.parquet",
            },
            {
                "id": "canon-telem-id-1",
                "normalization_run_id": "norm-run-id-1",
                "season": 2024,
                "event_name": "Bahrain",
                "session_type": "Q",
                "driver_code": "VER",
                "asset_type": "telemetry",
                "storage_path": "data/interim/canonical/2024/bahrain/Q/telemetry/VER.parquet",
            },
        ]
        return mock_response
    
    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute = _mock_execute
    
    repo.client.table().select.return_value = mock_query
    return repo


@pytest.fixture
def mock_feature_assets_repo():
    repo = MagicMock()
    repo.find_existing.return_value = None  # Force generation
    return repo


@pytest.fixture
def mock_feature_runs_repo():
    repo = MagicMock()
    repo.create_started.return_value = {"id": "test-feature-run-id"}
    return repo


def test_layer2_pipeline_end_to_end(
    tmp_path,
    mock_canonical_repo,
    mock_feature_assets_repo,
    mock_feature_runs_repo,
    monkeypatch,
):
    """Test full Layer 2 pipeline with mocked Supabase."""
    # 1. Setup mock canonical data on disk
    base_dir = tmp_path / "f1_pipeline"
    canon_dir = base_dir / "data/interim/canonical/2024/bahrain/Q"
    canon_dir.mkdir(parents=True, exist_ok=True)
    telem_dir = canon_dir / "telemetry"
    telem_dir.mkdir(parents=True, exist_ok=True)
    
    # Create simple telemetry parquet
    telem_df = pd.DataFrame({
        "time": pd.to_timedelta(np.arange(10) * 0.1, unit="s"),
        "speed": np.linspace(100, 300, 10),
        "distance": np.arange(10) * 5.0,
        "x": np.zeros(10),
        "y": np.arange(10) * 5.0,
        "throttle": np.full(10, 100),
        "brake": np.zeros(10),
    })
    telem_path = telem_dir / "VER.parquet"
    telem_df.to_parquet(telem_path, index=False)
    
    # Create simple laps parquet
    laps_df = pd.DataFrame({
        "driver_code": ["VER"],
        "lap_number": [1],
        "lap_time": [pd.Timedelta(seconds=90)],
        "stint": [1],
        "compound": ["SOFT"],
    })
    laps_path = canon_dir / "laps.parquet"
    laps_df.to_parquet(laps_path, index=False)
    
    # Monkeypatch PROJECT_ROOT so it resolves storage paths to tmp_path
    import f1_pipeline.features.feature_pipeline
    monkeypatch.setattr(f1_pipeline.features.feature_pipeline, "PROJECT_ROOT", base_dir)
    monkeypatch.setattr(f1_pipeline.features.feature_pipeline, "PATHS", MagicMock(interim=base_dir / "data/interim"))
    
    # 2. Execute pipeline
    pipeline = Layer2Pipeline(
        canonical_assets=mock_canonical_repo,
        feature_assets=mock_feature_assets_repo,
        feature_runs=mock_feature_runs_repo,
        features_config={},
    )
    request = Layer2FeatureRequest(
        season=2024,
        event="Bahrain",
        session_type="Q",
        driver_code="VER",
        feature_sets=["all"],
        force=True,
    )
    result = pipeline.run(request)
    
    # 3. Assertions
    assert result.success is True
    assert result.feature_run_id == "test-feature-run-id"
    assert len(result.assets) == 3  # telemetry, laps, stints (corners may be empty)
    
    # Check outputs exist
    feature_dir = base_dir / "data/interim/features/2024/bahrain/Q"
    assert (feature_dir / "metadata.json").exists()
    assert (feature_dir / "session_summary.parquet").exists()
    assert (feature_dir / "telemetry/ver.parquet").exists()
    assert (feature_dir / "laps/ver.parquet").exists()
    assert (feature_dir / "stints/ver.parquet").exists()
    
    # Check repos were called
    mock_feature_runs_repo.create_started.assert_called_once()
    mock_feature_runs_repo.mark_success.assert_called_once_with("test-feature-run-id")
    assert mock_feature_assets_repo.create_asset.call_count >= 3
