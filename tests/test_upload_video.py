from fastapi.testclient import TestClient
from uuid import UUID
from pathlib import Path

import pytest

from src.upload_service.app import create_app
from src.upload_service.domain import VideoEventPublisher, VideoUploadedEvent
from tests.conftest import FakeVideoEventPublisher


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


@pytest.fixture
def fake_publisher(fake_video_publisher) -> FakeVideoEventPublisher:
    """Alias the global fake_video_publisher fixture."""
    return fake_video_publisher


@pytest.fixture
def client(fake_publisher: FakeVideoEventPublisher) -> TestClient:
    app = create_app(fake_publisher)
    return TestClient(app)


@pytest.fixture
def files(some_filename: str, some_file_content: bytes, some_file_mimetype: str) -> dict:
    return {
        "file": (some_filename, some_file_content, some_file_mimetype),
    }


# --- Unit Tests ---


@pytest.mark.unit
def test_should_return_201_and_video_info_when_file_uploaded(
    client: TestClient,
    files: dict,
    some_filename: str,
):
    response = client.post("/videos", files=files)

    assert response.status_code == 201

    body = response.json()
    assert isinstance(body, dict)

    assert "video_id" in body
    assert isinstance(body["video_id"], str)
    assert body["video_id"] != ""

    UUID(body["video_id"])

    assert "filename" in body
    assert body["filename"] == some_filename


@pytest.mark.unit
def test_should_return_422_when_file_field_missing(client: TestClient):
    response = client.post("/videos", files={})

    assert response.status_code == 422


@pytest.mark.integration
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

    assert response.status_code == 201
    body = response.json()
    assert "video_id" in body
    video_id = body["video_id"]
    UUID(video_id)
    assert body["filename"] == some_filename

    expected_path = tmp_path / "data" / "uploads" / video_id / some_filename
    assert expected_path.is_file()

    contents = expected_path.read_bytes()
    assert contents == some_file_content


@pytest.mark.integration
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

    assert response.status_code == 201
    body = response.json()
    video_id = body["video_id"]
    UUID(video_id)
    assert body["filename"] == some_filename

    assert len(fake_publisher.published) == 1

    event = fake_publisher.published[0]
    assert event.video_id == video_id
    assert event.filename == some_filename

    expected_path = Path("data") / "uploads" / video_id / some_filename
    assert Path(event.storage_path) == expected_path


@pytest.mark.unit
@pytest.mark.parametrize("invalid_files,description", [
    ({}, "missing file field"),
    ({"wrong_field": ("test.mp4", b"content", "video/mp4")}, "wrong field name"),
])
def test_should_return_422_for_invalid_file_uploads(
    client: TestClient,
    invalid_files: dict,
    description: str,
):
    response = client.post("/videos", files=invalid_files)

    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.parametrize("filename,mimetype", [
    ("test.mp4", "video/mp4"),
    ("session.mov", "video/quicktime"),
    ("recording.avi", "video/x-msvideo"),
    ("clip.webm", "video/webm"),
])
def test_should_accept_various_video_formats(
    client: TestClient,
    some_file_content: bytes,
    filename: str,
    mimetype: str,
):
    files = {"file": (filename, some_file_content, mimetype)}
    
    response = client.post("/videos", files=files)

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == filename