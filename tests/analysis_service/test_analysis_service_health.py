import pytest
from fastapi.testclient import TestClient

from src.analysis_service.app import app, create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.unit
def test_should_return_200_status_code_when_health_endpoint_called(client: TestClient):
    response = client.get("/health")

    expected_status = 200
    actual_status = response.status_code
    assert actual_status == expected_status


@pytest.mark.unit
def test_should_return_ok_json_when_health_endpoint_called(client: TestClient):
    response = client.get("/health")

    expected_json = {"status": "ok"}
    actual_json = response.json()
    assert actual_json == expected_json


@pytest.mark.unit
def test_should_create_app_instance_with_create_app_function():
    from fastapi import FastAPI

    app_instance = create_app()

    assert isinstance(app_instance, FastAPI)
