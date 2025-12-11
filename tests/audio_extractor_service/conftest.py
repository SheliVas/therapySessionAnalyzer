import pytest
from pathlib import Path
from datetime import datetime
from typing import Optional
from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import AudioExtractedEvent


class FakeStorageClient:
    """Fake StorageClient that records download/upload calls."""
    def __init__(self) -> None:
        self.download_response: Optional[bytes] = None
        self.download_called_with: Optional[dict] = None
        self.upload_called_with: Optional[dict] = None
    
    def set_download_response(self, content: bytes) -> None:
        """Set the response for download_file calls."""
        self.download_response = content
    
    def download_file(self, bucket: str, key: str) -> bytes:
        """Record the call and return the set response."""
        self.download_called_with = {"bucket": bucket, "key": key}
        return self.download_response or b""
    
    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        """Record the upload call."""
        self.upload_called_with = {"bucket": bucket, "key": key, "content": content}


class FakeAudioConverter:
    """Fake AudioConverter that records convert calls."""
    def __init__(self) -> None:
        self.convert_response: Optional[bytes] = None
        self.convert_called_with: Optional[bytes] = None
    
    def set_convert_response(self, content: bytes) -> None:
        """Set the response for convert calls."""
        self.convert_response = content
    
    def convert(self, video_bytes: bytes) -> bytes:
        """Record the call and return the set response."""
        self.convert_called_with = video_bytes
        return self.convert_response or b"fake-audio-bytes"


class FakeAudioEventPublisher:
    def __init__(self) -> None:
        self.published_events: list[AudioExtractedEvent] = []

    def publish_audio_extracted(self, event: AudioExtractedEvent) -> None:
        self.published_events.append(event)


# --- Fixtures: Fakes ---

@pytest.fixture
def fake_storage_client() -> FakeStorageClient:
    """Fixture for FakeStorageClient."""
    return FakeStorageClient()


@pytest.fixture
def fake_audio_converter() -> FakeAudioConverter:
    """Fixture for FakeAudioConverter."""
    return FakeAudioConverter()


@pytest.fixture
def fake_audio_publisher() -> FakeAudioEventPublisher:
    """Fixture for FakeAudioEventPublisher."""
    return FakeAudioEventPublisher()


# --- Fixtures: Test Data ---

@pytest.fixture
def video_id() -> str:
    """Default test video ID."""
    return "test-video-id"


@pytest.fixture
def video_bytes() -> bytes:
    """Default test video bytes."""
    return b"fake-video-content"


@pytest.fixture
def audio_bytes() -> bytes:
    """Default test audio bytes."""
    return b"fake-audio-content"


@pytest.fixture
def filename() -> str:
    """Default test filename."""
    return "test.mp4"


@pytest.fixture
def video_uploaded_event(video_id: str, filename: str) -> VideoUploadedEvent:
    """Create a VideoUploadedEvent with default values."""
    return VideoUploadedEvent(
        video_id=video_id,
        filename=filename,
        bucket="therapy-videos",
        key=f"videos/{video_id}/{filename}",
        uploaded_at=datetime.now(),
    )


# --- Fixtures: Pre-configured Fakes ---

@pytest.fixture
def configured_storage_and_converter(
    fake_storage_client: FakeStorageClient,
    fake_audio_converter: FakeAudioConverter,
    video_bytes: bytes,
    audio_bytes: bytes,
):
    """Pre-configure storage client and converter with happy path responses."""
    fake_storage_client.set_download_response(video_bytes)
    fake_audio_converter.set_convert_response(audio_bytes)
    return fake_storage_client, fake_audio_converter


# --- Legacy Fixtures (for backwards compatibility with existing tests) ---

@pytest.fixture
def video_path(tmp_path: Path, filename: str, video_bytes: bytes) -> Path:
    path = tmp_path / filename
    path.write_bytes(video_bytes)
    return path


@pytest.fixture
def base_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "data" / "audio_extractor_output"


@pytest.fixture
def fake_publisher() -> FakeAudioEventPublisher:
    return FakeAudioEventPublisher()

