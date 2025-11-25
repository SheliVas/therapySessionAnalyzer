from fastapi.testclient import TestClient
from uuid import UUID
from pathlib import Path

from src.upload_service.app import app

# - **upload_service** (FastAPI)
#   - Endpoint: `POST /videos`
#   - Accepts video file upload.
#   - Stores raw video in MinIO (e.g., bucket `therapy-videos`).
#   - Publishes RabbitMQ event `video.uploaded` with payload: video ID, MinIO path, metadata.

some_filename = "session1.mp4"
some_file_content = b"fake-video-content"
some_file_mimetype = "video/mp4"

def test_should_return_201_and_video_info_when_file_uploaded():
    client = TestClient(app)

    files = {
        "file": (some_filename, some_file_content, some_file_mimetype),
    }

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


def test_should_return_422_when_file_field_missing():
    client = TestClient(app)

    response = client.post("/videos", files={})

    assert response.status_code == 422, f"expected 422, got {response.status_code}"


def test_should_save_uploaded_file_to_disk_when_video_uploaded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    files = {
        "file": (some_filename, some_file_content, some_file_mimetype),
    }

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