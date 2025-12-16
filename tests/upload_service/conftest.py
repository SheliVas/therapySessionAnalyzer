import pytest
from fastapi.testclient import TestClient

from src.upload_service.app import create_app
from src.upload_service.domain import (
    VideoUploadedEvent,
    VideoEventPublisher,
    VideosRepository,
    StorageClient,
)
from datetime import datetime


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


class FakeVideosRepository(VideosRepository):
    """Fake repository for testing."""
    def __init__(self):
        self.videos = []

    def upsert_on_upload(
        self,
        video_id: str,
        filename: str,
        storage_path: str,
        uploaded_at: datetime,
    ) -> None:
        self.videos.append({
            "video_id": video_id,
            "filename": filename,
            "storage_path": storage_path,
            "uploaded_at": uploaded_at,
        })


@pytest.fixture
def fake_storage() -> FakeStorageClient:
    """Fake storage client for testing."""
    return FakeStorageClient()


@pytest.fixture
def fake_publisher() -> FakeVideoEventPublisher:
    """Fake event publisher for testing."""
    return FakeVideoEventPublisher()


@pytest.fixture
def fake_repository() -> FakeVideosRepository:
    """Fake repository for testing."""
    return FakeVideosRepository()


@pytest.fixture
def client(
    fake_storage: FakeStorageClient,
    fake_publisher: FakeVideoEventPublisher,
    fake_repository: FakeVideosRepository,
) -> TestClient:
    """Create FastAPI test client with injected fake dependencies."""
    app = create_app(
        storage_client=fake_storage,
        publisher=fake_publisher,
        repository=fake_repository,
    )
    return TestClient(app)


