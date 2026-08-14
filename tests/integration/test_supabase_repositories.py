from __future__ import annotations

import os

import pytest

from f1_pipeline.db.repositories.ingestion_runs import IngestionRunsRepository
from f1_pipeline.db.repositories.raw_assets import RawAssetsRepository
from f1_pipeline.db.supabase_client import health_check


pytestmark = pytest.mark.integration


def _requires_supabase() -> None:
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        pytest.skip("Supabase credentials are not configured.")


def test_supabase_health_check() -> None:
    _requires_supabase()
    assert health_check()


def test_ingestion_run_and_raw_asset_repository_round_trip() -> None:
    _requires_supabase()
    runs = IngestionRunsRepository()
    assets = RawAssetsRepository(runs.client)

    run = runs.create_started(season=2024, event_name="Bahrain", session_type="Q", driver_code="VER")
    asset = assets.create_asset(
        ingestion_run_id=run["id"],
        source="fastf1",
        asset_type="test_asset",
        season=2024,
        event_name="Bahrain",
        session_type="Q",
        driver_code="VER",
        lap_number=None,
        storage_path="data/raw/test.parquet",
        file_format="parquet",
        checksum="0" * 64,
        row_count=0,
    )
    runs.mark_success(run["id"])

    assert asset["ingestion_run_id"] == run["id"]
    assert runs.get_by_id(run["id"])["status"] == "success"
