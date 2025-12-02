from fastapi.testclient import TestClient
from uuid import UUID
from pathlib import Path

import pytest

from src.upload_service.app import create_app
from src.upload_service.events import VideoEventPublisher, VideoUploadedEvent


# --- Fixtures ---

@pytest.fixture
def some_filename() -> str:
    return "session1.mp4"


@pytest.fixture
def some_file_content() -> bytes:
    return b"fake-video-content"


@pytest.fixture
def some_file_mimetype() -> str:
    return "video/mp4"


class FakeVideoEventPublisher(VideoEventPublisher):
    def __init__(self) -> None:
        self.published: list[VideoUploadedEvent] = []

    def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
        self.published.append(event)


@pytest.fixture
def fake_publisher() -> FakeVideoEventPublisher:
    return FakeVideoEventPublisher()


@pytest.fixture
def client(fake_publisher: FakeVideoEventPublisher) -> TestClient:
    app = create_app(fake_publisher)
    return TestClient(app)


@pytest.fixture
def files(some_filename: str, some_file_content: bytes, some_file_mimetype: str) -> dict:
    return {
        "file": (some_filename, some_file_content, some_file_mimetype),
    }


# --- Tests ---

def test_should_return_201_and_video_info_when_file_uploaded(
    client: TestClient,
    files: dict,
    some_filename: str,
):
    response = client.post("/videos", files=files)

    assert response.status_code == 201, f"expected 201, got {response.status_code}"

    body = response.json()
    assert isinstance(body, dict)

    assert "video_id" in body, f"response body missing 'video_id': {body}"
    assert isinstance(body["video_id"], str), f"'video_id' is not a string: {body['video_id']}"
    assert body["video_id"] != "", "'video_id' is an empty string"

    UUID(body["video_id"])

    assert "filename" in body, f"response body missing 'filename': {body}"
    assert body["filename"] == some_filename, f"expected filename '{some_filename}', got '{body['filename']}'"


def test_should_return_422_when_file_field_missing(client: TestClient):
    response = client.post("/videos", files={})

    assert response.status_code == 422, f"expected 422, got {response.status_code}"


def test_should_save_uploaded_file_to_disk_when_video_uploaded(
    tmp_path: Path,
    monkeypatch,
    fake_publisher: FakeVideoEventPublisher,
    files: dict,
    some_filename: str,
    some_file_content: bytes,
):
    monkeypatch.chdir(tmp_path)
    app = create_app(fake_publisher)
    client = TestClient(app)

    response = client.post("/videos", files=files)

    assert response.status_code == 201, f"expected 201, got {response.status_code}"
    body = response.json()
    assert "video_id" in body, f"response body missing 'video_id': {body}"
    video_id = body["video_id"]
    UUID(video_id)
    assert body["filename"] == some_filename

    expected_path = tmp_path / "data" / "uploads" / video_id / some_filename
    assert expected_path.is_file(), f"expected file at {expected_path}, but it does not exist"

    contents = expected_path.read_bytes()
    assert contents == some_file_content, f"expected file contents {some_file_content}, got {contents}"


def test_should_publish_video_uploaded_event_when_video_uploaded(
    tmp_path: Path,
    monkeypatch,
    fake_publisher: FakeVideoEventPublisher,
    files: dict,
    some_filename: str,
):
    monkeypatch.chdir(tmp_path)
    app = create_app(fake_publisher)
    client = TestClient(app)

    response = client.post("/videos", files=files)

    assert response.status_code == 201, f"expected 201, got {response.status_code}"
    body = response.json()
    video_id = body["video_id"]
    UUID(video_id)
    assert body["filename"] == some_filename, f"expected filename '{some_filename}', got '{body['filename']}'"

    assert len(fake_publisher.published) == 1, f"expected 1 event, got {len(fake_publisher.published)}"

    event = fake_publisher.published[0]
    assert event.video_id == video_id, f"expected video_id '{video_id}', got '{event.video_id}'"
    assert event.filename == some_filename, f"expected filename '{some_filename}', got '{event.filename}'"

    expected_path = Path("data") / "uploads" / video_id / some_filename
    assert Path(event.storage_path) == expected_path, f"expected storage_path '{expected_path}', got '{event.storage_path}'"