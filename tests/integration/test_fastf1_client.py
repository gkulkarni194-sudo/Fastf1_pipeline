from __future__ import annotations

import pytest

from f1_pipeline.ingestion.clients.fastf1_client import FastF1Client


pytestmark = pytest.mark.integration


def test_fastf1_loads_reference_session(tmp_path) -> None:
    client = FastF1Client(cache_dir=tmp_path / "fastf1-cache")
    session = client.load_session(2024, "Bahrain", "Q")

    assert not session.laps.empty
