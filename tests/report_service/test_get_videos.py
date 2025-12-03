import pytest
from fastapi.testclient import TestClient
from src.report_service.app import create_app, ReportRepository
from src.report_service.mongo_repository import VideoSummary


class FakeReportRepository(ReportRepository):
    def __init__(self, videos: list[VideoSummary]) -> None:
        self.videos = videos
    
    def list_videos(self) -> list[VideoSummary]:
        return self.videos

    def get_video(self, video_id: str) -> VideoSummary | None:
        return next((v for v in self.videos if v.video_id == video_id), None)


@pytest.fixture
def sample_videos() -> list[VideoSummary]:
    return [
        VideoSummary(video_id="video-1", word_count=10, extra={"foo": "bar"}),
        VideoSummary(video_id="video-2", word_count=20, extra={"foo": "baz"}),
    ]


@pytest.fixture
def fake_repository(sample_videos) -> FakeReportRepository:
    return FakeReportRepository(sample_videos)


@pytest.fixture
def client(fake_repository):
    app = create_app(fake_repository)
    return TestClient(app)


def test_should_return_200_when_videos_endpoint_called(client):
    response = client.get("/videos")
    
    assert response.status_code == 200, f"expected status code 200, got {response.status_code}"


def test_should_return_videos_list_as_json(client, sample_videos):
    response = client.get("/videos")
    data = response.json()
    
    assert isinstance(data, list), f"expected list, got {type(data)}"
    assert len(data) == 2, f"expected 2 videos, got {len(data)}"


def test_should_return_video_1_data(client, sample_videos):
    response = client.get("/videos")
    data = response.json()
    
    video_1 = next((v for v in data if v["video_id"] == "video-1"), None)
    assert video_1 is not None, "expected to find video-1 in results"
    assert video_1["word_count"] == 10, f"expected word_count 10, got {video_1['word_count']}"
    assert video_1["extra"] == {"foo": "bar"}, f"expected extra {{'foo': 'bar'}}, got {video_1['extra']}"


def test_should_return_video_2_data(client, sample_videos):
    response = client.get("/videos")
    data = response.json()
    
    video_2 = next((v for v in data if v["video_id"] == "video-2"), None)
    assert video_2 is not None, "expected to find video-2 in results"
    assert video_2["word_count"] == 20, f"expected word_count 20, got {video_2['word_count']}"
    assert video_2["extra"] == {"foo": "baz"}, f"expected extra {{'foo': 'baz'}}, got {video_2['extra']}"
