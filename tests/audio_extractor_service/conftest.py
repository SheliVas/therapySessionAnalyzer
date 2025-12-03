import pytest
from pathlib import Path
from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import AudioExtractedEvent


class FakeAudioEventPublisher:
    def __init__(self) -> None:
        self.published_events: list[AudioExtractedEvent] = []

    def publish_audio_extracted(self, event: AudioExtractedEvent) -> None:
        self.published_events.append(event)


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


@pytest.fixture
def fake_publisher() -> FakeAudioEventPublisher:
    return FakeAudioEventPublisher()
