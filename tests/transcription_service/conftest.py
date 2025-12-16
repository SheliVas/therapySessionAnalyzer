import pytest
from pathlib import Path
from typing import Optional
from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import (
    TranscriptCreatedEvent,
    TranscriptionBackend,
    StorageClient,
)
from src.transcription_service.worker import TranscriptEventPublisher


class FakeTranscriptionBackend(TranscriptionBackend):
    def __init__(self, transcript_text: str) -> None:
        self.transcript_text = transcript_text
        self.calls: list[bytes] = []

    def transcribe(self, audio_bytes: bytes) -> str:
        self.calls.append(audio_bytes)
        return self.transcript_text


class FakeTranscriptEventPublisher(TranscriptEventPublisher):
    def __init__(self) -> None:
        self.published_events: list[TranscriptCreatedEvent] = []

    def publish_transcript_created(self, event: TranscriptCreatedEvent) -> None:
        self.published_events.append(event)


class FakeStorageClient:
    """Fake StorageClient that records download/upload calls."""
    def __init__(self) -> None:
        self.download_response: Optional[bytes] = None
        self.download_called_with: Optional[dict] = None
        self.upload_called_with: Optional[dict] = None
    
    def set_download_response(self, content: bytes) -> None:
        self.download_response = content
    
    def download_file(self, bucket: str, key: str) -> bytes:
        self.download_called_with = {"bucket": bucket, "key": key}
        return self.download_response or b""
    
    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        self.upload_called_with = {"bucket": bucket, "key": key, "content": content}


class FakeVideosRepository:
    """Fake repository for testing video status updates."""
    def __init__(self) -> None:
        self.mark_transcribed_calls: list[dict] = []
        self.should_raise_error = False
    
    def mark_transcribed(self, video_id: str, transcript_path: str) -> None:
        """Record the call."""
        self.mark_transcribed_calls.append({
            "video_id": video_id,
            "transcript_path": transcript_path,
        })
        if self.should_raise_error:
            raise ValueError("Repository error")


@pytest.fixture
def audio_bytes() -> bytes:
    return b"fake audio content"


@pytest.fixture
def event() -> AudioExtractedEvent:
    return AudioExtractedEvent(
        video_id="video-123",
        bucket="therapy-audio",
        key="audio/video-123/audio.mp3",
    )


@pytest.fixture
def fake_backend() -> FakeTranscriptionBackend:
    return FakeTranscriptionBackend(transcript_text="hello transcript")


@pytest.fixture
def fake_publisher() -> FakeTranscriptEventPublisher:
    return FakeTranscriptEventPublisher()


@pytest.fixture
def fake_storage(audio_bytes: bytes) -> FakeStorageClient:
    client = FakeStorageClient()
    client.set_download_response(audio_bytes)
    return client


@pytest.fixture
def fake_videos_repository() -> FakeVideosRepository:
    """Fixture for FakeVideosRepository."""
    return FakeVideosRepository()

