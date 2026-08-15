import pytest
from fastapi.testclient import TestClient

from f1_pipeline.api.app import app
from f1_pipeline.api.services.metadata_service import MetadataService

client = TestClient(app)

def mock_get_seasons(self):
    return [2023, 2024]

def test_get_seasons(monkeypatch):
    monkeypatch.setattr(MetadataService, "get_seasons", mock_get_seasons)
    response = client.get("/api/v1/seasons")
    assert response.status_code == 200
    data = response.json()
    assert data == [2023, 2024]
