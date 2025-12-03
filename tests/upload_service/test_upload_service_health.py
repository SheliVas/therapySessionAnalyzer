from fastapi.testclient import TestClient
from src.upload_service.app import create_app

def test_health_endpoint_returns_ok(fake_publisher):
    app = create_app(fake_publisher)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
