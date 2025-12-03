import pytest
from fastapi.testclient import TestClient
from src.report_service.app import create_app, ReportRepository
from src.report_service.mongo_repository import VideoSummary

class FakeReportRepository(ReportRepository):
    def __init__(self):
        self.videos = {
            "video-1": VideoSummary(video_id="video-1", word_count=100, extra={"a": 1})
        }

    def list_videos(self) -> list[VideoSummary]:
        return list(self.videos.values())

    def get_video(self, video_id: str) -> VideoSummary | None:
        return self.videos.get(video_id)

@pytest.fixture
def client():
    repo = FakeReportRepository()
    app = create_app(repo)
    return TestClient(app)

def test_get_video_success(client):
    response = client.get("/videos/video-1")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["video_id"] == "video-1"
    assert data["word_count"] == 100
    assert data["extra"] == {"a": 1}

def test_get_video_not_found(client):
    response = client.get("/videos/missing")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
