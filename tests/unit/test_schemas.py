from __future__ import annotations

import pytest

from f1_pipeline.ingestion.schemas import Layer0IngestionRequest


def test_request_normalizes_session_and_driver() -> None:
    request = Layer0IngestionRequest(season=2024, event="Bahrain", session_type="q", driver_code="ver")

    assert request.session_type == "Q"
    assert request.driver_code == "VER"


def test_request_rejects_unknown_session() -> None:
    with pytest.raises(ValueError):
        Layer0IngestionRequest(season=2024, event="Bahrain", session_type="P4")
