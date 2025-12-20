import pytest


# --- Unit Tests ---


@pytest.mark.unit
@pytest.mark.parametrize("video_id, expected_word_count, expected_status, expected_analysis", [
    ("video-1", 10, "analyzed", {"foo": "bar", "recommendations": {"therapist_recommendations": [{"title": "Rec 1", "priority": "high"}]}}),
    ("video-2", 20, "analyzed", {"foo": "baz", "recommendations": {"therapist_recommendations": [{"title": "Rec 2", "priority": "low"}]}}),
])
def test_get_video_success(client, video_id, expected_word_count, expected_status, expected_analysis):
    response = client.get(f"/videos/{video_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == video_id
    assert data["word_count"] == expected_word_count
    assert data["status"] == expected_status
    assert data["analysis"] == expected_analysis
    assert "recommendations" in data["analysis"]
    assert data["analysis"]["recommendations"] == expected_analysis["recommendations"]


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
