import pytest
from fastapi.testclient import TestClient
from src.report_service.app import create_app, ReportRepository
from src.report_service.mongo_repository import VideoSummary


class FakeReportRepository(ReportRepository):
    def __init__(self, videos: list[VideoSummary] | None = None) -> None:
        self.videos = videos or []
    
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
