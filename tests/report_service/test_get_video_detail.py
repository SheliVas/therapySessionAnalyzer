import pytest


# --- Unit Tests ---


@pytest.mark.unit
@pytest.mark.parametrize("video_id, expected_word_count, expected_extra", [
    ("video-1", 10, {"foo": "bar"}),
    ("video-2", 20, {"foo": "baz"}),
])
def test_get_video_success(client, video_id, expected_word_count, expected_extra):
    response = client.get(f"/videos/{video_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["video_id"] == video_id
    assert data["word_count"] == expected_word_count
    assert data["extra"] == expected_extra


@pytest.mark.unit
@pytest.mark.parametrize("invalid_id", [
    "missing",
    "video-999",
    "special_chars_!@#",
    "   ",  # whitespace
])
def test_get_video_not_found(client, invalid_id):
    response = client.get(f"/videos/{invalid_id}")
    assert response.status_code == 404
