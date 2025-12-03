from pathlib import Path

import pytest

from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import (
    AudioExtractedEvent,
    handle_video_uploaded,
)


# --- Fixtures ---

@pytest.fixture
def video_bytes() -> bytes:
    return b"fake-video-content"


@pytest.fixture
def video_id() -> str:
    return "video-123"


@pytest.fixture
def filename() -> str:
    return "video.mp4"


@pytest.fixture
def video_path(tmp_path: Path, filename: str, video_bytes: bytes) -> Path:
    path = tmp_path / filename
    path.write_bytes(video_bytes)
    return path


@pytest.fixture
def base_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "data" / "audio"


@pytest.fixture
def event(video_id: str, filename: str, video_path: Path) -> VideoUploadedEvent:
    return VideoUploadedEvent(
        video_id=video_id,
        filename=filename,
        storage_path=str(video_path),
    )


# --- Tests ---

def test_should_return_audio_extracted_event_with_correct_fields(
    event: VideoUploadedEvent,
    base_output_dir: Path,
    video_id: str,
):
    result = handle_video_uploaded(event=event, base_output_dir=base_output_dir)

    assert isinstance(result, AudioExtractedEvent)
    assert result.video_id == video_id

    audio_path = Path(result.audio_path)
    expected_audio_path = base_output_dir / video_id / "audio.mp3"
    assert audio_path == expected_audio_path


def test_should_write_audio_file_to_disk(
    event: VideoUploadedEvent,
    base_output_dir: Path,
    video_id: str,
    video_bytes: bytes,
):
    result = handle_video_uploaded(event=event, base_output_dir=base_output_dir)

    audio_path = Path(result.audio_path)
    assert audio_path.is_file(), f"expected audio file at {audio_path}, but it does not exist"

    written_bytes = audio_path.read_bytes()
    assert written_bytes == video_bytes, (
        f"expected audio bytes {video_bytes!r}, got {written_bytes!r}"
    )