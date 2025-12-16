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
def fake_storage(fake_storage_client, audio_bytes: bytes):
    """Configured FakeStorageClient with audio_bytes pre-loaded."""
    fake_storage_client.set_download_response(audio_bytes)
    return fake_storage_client
