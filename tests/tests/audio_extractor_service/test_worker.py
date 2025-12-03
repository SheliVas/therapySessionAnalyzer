from pathlib import Path

import pytest

from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import AudioExtractedEvent
from src.audio_extractor_service.worker import (
    AudioEventPublisher,
    process_video_uploaded_event,
)


# --- Fixtures ---

@pytest.fixture
def video_bytes() -> bytes:
    return b"fake-video-content"


@pytest.fixture
def video_id() -> str:
    return "some-video-id"


@pytest.fixture
def filename() -> str:
    return "some-video.mp4"


@pytest.fixture
def video_path(tmp_path: Path, filename: str, video_bytes: bytes) -> Path:
    path = tmp_path / filename
    path.write_bytes(video_bytes)
    return path


@pytest.fixture
def base_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "data" / "audio_extractor_output"


@pytest.fixture
def event(video_id: str, filename: str, video_path: Path) -> VideoUploadedEvent:
    return VideoUploadedEvent(
        video_id=video_id,
        filename=filename,
        storage_path=str(video_path),
    )


class FakeAudioEventPublisher:
    def __init__(self) -> None:
        self.published_events: list[AudioExtractedEvent] = []

    def publish_audio_extracted(self, event: AudioExtractedEvent) -> None:
        self.published_events.append(event)


@pytest.fixture
def fake_publisher() -> FakeAudioEventPublisher:
    return FakeAudioEventPublisher()


# --- Tests ---

def test_should_return_audio_extracted_event_and_write_audio_file(
    event: VideoUploadedEvent,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    video_id: str,
    video_bytes: bytes,
):
    result = process_video_uploaded_event(
        event=event,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    assert isinstance(result, AudioExtractedEvent), f"expected AudioExtractedEvent, got {type(result)}"
    assert result.video_id == video_id, f"expected video_id {video_id}, got {result.video_id}"

    audio_path = Path(result.audio_path)
    expected_audio_path = base_output_dir / video_id / "audio.mp3"
    assert audio_path == expected_audio_path, f"expected audio_path {expected_audio_path}, got {audio_path}"
    assert audio_path.is_file(), f"expected audio file at {audio_path}, but it does not exist"

    written_bytes = audio_path.read_bytes()
    assert written_bytes == video_bytes, "expected audio file content to match video content"


def test_should_publish_audio_extracted_event_via_publisher(
    event: VideoUploadedEvent,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
):
    result = process_video_uploaded_event(
        event=event,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    assert len(fake_publisher.published_events) == 1, "expected one published event"

    published_event = fake_publisher.published_events[0]
    assert published_event.video_id == result.video_id, f"expected video_id {result.video_id}, got {published_event.video_id}"
    assert published_event.audio_path == result.audio_path, f"expected audio_path {result.audio_path}, got {published_event.audio_path}"
