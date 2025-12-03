from fastapi.testclient import TestClient
from src.report_service.app import create_app


def test_health_endpoint_returns_ok():
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200, f"expected status code 200, got {response.status_code}"
    assert response.json() == {"status": "ok"}, f"expected {{'status': 'ok'}}, got {response.json()}"
