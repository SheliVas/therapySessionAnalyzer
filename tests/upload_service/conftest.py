import pytest
from src.upload_service.domain import VideoEventPublisher, VideoUploadedEvent

class FakeVideoEventPublisher(VideoEventPublisher):
    def __init__(self) -> None:
        self.published: list[VideoUploadedEvent] = []

    def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
        self.published.append(event)

@pytest.fixture
def fake_publisher():
    return FakeVideoEventPublisher()
