import pytest
from fastapi.testclient import TestClient

from src.upload_service.app import create_app
from src.upload_service.domain import VideoUploadedEvent, VideoEventPublisher
from src.upload_service.storage import StorageClient


class FakeStorageClient(StorageClient):
    """Fake MinIO client for testing."""
    def __init__(self):
        self.uploads: list[dict] = []

    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        self.uploads.append({
            "bucket": bucket,
            "key": key,
            "content_length": len(content),
        })


class FakeVideoEventPublisher(VideoEventPublisher):
    """Fake publisher for upload service tests."""
    def __init__(self):
        self.published_events: list[VideoUploadedEvent] = []

    def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
        self.published_events.append(event)


@pytest.fixture
def fake_storage() -> FakeStorageClient:
    """Fake storage client for testing."""
    return FakeStorageClient()


@pytest.fixture
def fake_publisher() -> FakeVideoEventPublisher:
    """Fake event publisher for testing."""
    return FakeVideoEventPublisher()


@pytest.fixture
def client(fake_storage: FakeStorageClient, fake_publisher: FakeVideoEventPublisher) -> TestClient:
    """Create FastAPI test client with injected fake dependencies."""
    app = create_app(storage_client=fake_storage, publisher=fake_publisher)
    return TestClient(app)


