import pytest


# --- Unit Tests ---


@pytest.mark.unit
def test_get_video_success(client):
    response = client.get("/videos/video-1")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["video_id"] == "video-1"
    assert data["word_count"] == 10
    assert data["extra"] == {"foo": "bar"}


@pytest.mark.unit
def test_get_video_not_found(client):
    response = client.get("/videos/missing")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
