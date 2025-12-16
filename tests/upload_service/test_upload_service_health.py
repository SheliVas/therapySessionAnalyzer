import pytest
from fastapi.testclient import TestClient
from src.upload_service.app import create_app


@pytest.mark.unit
def test_health_endpoint_returns_ok(fake_storage, fake_publisher, fake_repository):
    app = create_app(storage_client=fake_storage, publisher=fake_publisher, repository=fake_repository)
