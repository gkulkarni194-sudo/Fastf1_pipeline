import pytest
from fastapi.testclient import TestClient

from f1_pipeline.api.app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    
def test_health_dependencies():
    response = client.get("/api/v1/health/dependencies")
    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "healthy"
    assert data["pipeline"] == "healthy"
