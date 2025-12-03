import pytest
from fastapi.testclient import TestClient

from src.transcription_service.app import app


@pytest.mark.unit
def test_should_return_ok_status_when_health_endpoint_called():
    """GET /health should return 200 with {"status": "ok"}."""
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
