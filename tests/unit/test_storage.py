from __future__ import annotations

import json

import pandas as pd

from f1_pipeline.ingestion.storage import StorageManager


def test_storage_manager_saves_parquet(tmp_path) -> None:
    manager = StorageManager()
    stored = manager.save_dataframe(pd.DataFrame({"Driver": ["VER"], "LapTime": ["1:29.1"]}), tmp_path / "laps.parquet")

    assert stored.file_format == "parquet"
    assert stored.row_count == 1
    assert len(stored.checksum) == 64
    assert pd.read_parquet(tmp_path / "laps.parquet").shape == (1, 2)


def test_storage_manager_saves_json(tmp_path) -> None:
    manager = StorageManager()
    stored = manager.save_json({"source": "fastf1"}, tmp_path / "metadata.json")

    assert stored.file_format == "json"
    assert stored.row_count == 1
    assert len(stored.checksum) == 64
    assert json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8")) == {"source": "fastf1"}
