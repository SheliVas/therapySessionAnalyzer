from fastapi.testclient import TestClient

from src.audio_extractor_service.app import app


def test_should_return_ok_status_when_health_endpoint_called():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}