import pytest
from datetime import datetime
from io import BytesIO
from fastapi.testclient import TestClient

from src.upload_service.domain import VideoUploadedEvent
from src.upload_service.storage import StorageClient
from src.upload_service.app import create_app
from tests.upload_service.conftest import FakeStorageClient, FakeVideoEventPublisher


@pytest.fixture
def failing_storage_client() -> StorageClient:
    """Storage client that raises an IOError."""
    class FailingStorageClient(StorageClient):
        def upload_file(self, bucket: str, key: str, content: bytes) -> None:
            raise IOError("Storage service unreachable")
    
    return FailingStorageClient()


@pytest.fixture
def failing_publisher() -> FakeVideoEventPublisher:
    """Publisher that raises a RuntimeError."""
    class FailingPublisher:
        def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
            raise RuntimeError("RabbitMQ is down")
    
    return FailingPublisher()


@pytest.mark.unit
@pytest.mark.parametrize(
    "filename,file_content",
    [
        ("session1.mp4", b"video data"),
        ("therapy_v2.mov", b"x" * 1000),
        ("file.avi", b"a"),
    ]
)
def test_should_upload_file_to_minio_and_return_201_when_filename_and_content_are_valid(
    client: TestClient,
    fake_storage: FakeStorageClient,
    filename: str,
    file_content: bytes,
) -> None:
    response = client.post(
        "/videos",
        files={"file": (filename, BytesIO(file_content), "video/*")},
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "video_id" in data
    assert data["filename"] == filename
    
    assert len(fake_storage.uploads) == 1
    upload = fake_storage.uploads[0]
    assert upload["bucket"] == "therapy-videos"
    assert upload["key"] == f"videos/{data['video_id']}/{filename}"
    assert upload["content_length"] == len(file_content)


@pytest.mark.unit
def test_should_publish_event_with_correct_metadata(
    client: TestClient,
    fake_publisher: FakeVideoEventPublisher,
) -> None:
    filename = "session1.mp4"
    file_content = b"video data"
    
    response = client.post(
        "/videos",
        files={"file": (filename, BytesIO(file_content), "video/mp4")},
    )
    
    assert response.status_code == 201
    video_id = response.json()["video_id"]
    
    assert len(fake_publisher.published_events) == 1
    event = fake_publisher.published_events[0]
    assert event.video_id == video_id
    assert event.filename == filename
    assert event.bucket == "therapy-videos"
    assert event.key == f"videos/{video_id}/{filename}"
    assert isinstance(event.uploaded_at, datetime)


@pytest.mark.unit
def test_should_include_uploaded_at_timestamp_in_event(
    client: TestClient,
    fake_publisher: FakeVideoEventPublisher,
) -> None:
    before = datetime.now()
    
    response = client.post(
        "/videos",
        files={"file": ("session1.mp4", BytesIO(b"data"), "video/mp4")},
    )
    
    after = datetime.now()
    
    assert response.status_code == 201
    event = fake_publisher.published_events[0]
    assert before <= event.uploaded_at <= after


@pytest.mark.unit
def test_should_return_400_when_file_is_empty(client: TestClient) -> None:
    response = client.post(
        "/videos",
        files={"file": ("empty.mp4", BytesIO(b""), "video/mp4")},
    )
    
    assert response.status_code == 400


@pytest.mark.unit
@pytest.mark.parametrize(
    "filename,expected_sanitized_substring",
    [
        ("session@#$.mp4", "session___.mp4"),
        ("file!@#$%^&*.mov", "file________.mov"),
        ("normal_file.avi", "normal_file.avi"),
        ("test (1) [backup].mp4", "test__1___backup_.mp4"),
    ]
)
def test_should_sanitize_special_characters_in_filename(
    client: TestClient,
    fake_storage: FakeStorageClient,
    filename: str,
    expected_sanitized_substring: str,
) -> None:
    response = client.post(
        "/videos",
        files={"file": (filename, BytesIO(b"data"), "video/mp4")},
    )
    
    assert response.status_code == 201
    video_id = response.json()["video_id"]
    
    upload = fake_storage.uploads[0]
    assert upload["key"] == f"videos/{video_id}/{expected_sanitized_substring}"


@pytest.mark.unit
def test_should_propagate_storage_failure_as_500(
    failing_storage_client: StorageClient,
    fake_publisher: FakeVideoEventPublisher,
) -> None:
    app = create_app(storage_client=failing_storage_client, publisher=fake_publisher)
    client = TestClient(app)
    
    response = client.post(
        "/videos",
        files={"file": ("session1.mp4", BytesIO(b"data"), "video/mp4")},
    )
    
    assert response.status_code == 500


@pytest.mark.unit
def test_should_propagate_publisher_failure_as_500(
    fake_storage: FakeStorageClient,
    failing_publisher,
) -> None:
    app = create_app(storage_client=fake_storage, publisher=failing_publisher)
    client = TestClient(app)
    
    response = client.post(
        "/videos",
        files={"file": ("session1.mp4", BytesIO(b"data"), "video/mp4")},
    )
    
    assert response.status_code == 500

