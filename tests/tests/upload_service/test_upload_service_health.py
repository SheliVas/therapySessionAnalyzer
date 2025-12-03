from fastapi.testclient import TestClient
from src.upload_service.app import create_app
from src.upload_service.domain import VideoEventPublisher, VideoUploadedEvent

class FakeVideoEventPublisher(VideoEventPublisher):
    def __init__(self) -> None:
        self.published: list[VideoUploadedEvent] = []

    def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
        self.published.append(event)

def test_health_endpoint_returns_ok():
    app = create_app(FakeVideoEventPublisher())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
