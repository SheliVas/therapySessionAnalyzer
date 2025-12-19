import pytest
from fastapi.testclient import TestClient
from src.report_service.app import create_app
from src.report_service.mongo_repository import VideoSummary


# --- Unit Tests ---


@pytest.mark.unit
def test_should_return_200_when_videos_endpoint_called(client):
    response = client.get("/videos")
    
    assert response.status_code == 200


@pytest.mark.unit
def test_should_return_videos_list_as_json(client, sample_videos):
    response = client.get("/videos")
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.unit
def test_should_not_return_non_analyzed_videos(fake_repository):
    fake_repository.videos.append(
        VideoSummary(video_id="video-3", word_count=0, status="uploaded", extra={})
    )
    app = create_app(fake_repository)
    client = TestClient(app)
    
    response = client.get("/videos")
    data = response.json()
    
    assert len(data) == 2
    assert all(v["status"] == "analyzed" for v in data)


@pytest.mark.unit
@pytest.mark.parametrize("video_id,expected_word_count,expected_status,expected_extra", [
    ("video-1", 10, "analyzed", {"foo": "bar", "recommendations": [{"title": "Rec 1", "priority": "high"}]}),
    ("video-2", 20, "analyzed", {"foo": "baz", "recommendations": [{"title": "Rec 2", "priority": "low"}]}),
])
def test_should_return_video_data(client, sample_videos, video_id, expected_word_count, expected_status, expected_extra):

    response = client.get("/videos")
    data = response.json()
    

    video = next((v for v in data if v["video_id"] == video_id), None)
    assert video is not None
    assert video["word_count"] == expected_word_count
    assert video["status"] == expected_status
    assert video["extra"] == expected_extra
