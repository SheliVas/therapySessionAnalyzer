"""Tests for transcription_service domain logic."""
from pathlib import Path
from typing import Optional

import pytest

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import (
    TranscriptCreatedEvent,
    TranscriptionBackend,
    generate_transcript,
    StorageClient,
)


class FakeTranscriptionBackend(TranscriptionBackend):
    """Fake backend that records calls and returns a fixed transcript."""

    def __init__(self, transcript_text: str) -> None:
        self.transcript_text = transcript_text
        self.calls: list[bytes] = []

    def transcribe(self, audio_bytes: bytes) -> str:
        self.calls.append(audio_bytes)
        return self.transcript_text


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


# --- Fixtures ---


@pytest.fixture
def audio_bytes() -> bytes:
    return b"fake audio content"


@pytest.fixture
def event() -> AudioExtractedEvent:
    """Create an AudioExtractedEvent for testing."""
    return AudioExtractedEvent(
        video_id="video-123",
        bucket="therapy-audio",
        key="audio/video-123/audio.mp3",
    )


@pytest.fixture
def fake_backend() -> FakeTranscriptionBackend:
    """Create a fake transcription backend."""
    return FakeTranscriptionBackend(transcript_text="hello world transcript")


@pytest.fixture
def fake_storage(audio_bytes: bytes) -> FakeStorageClient:
    client = FakeStorageClient()
    client.set_download_response(audio_bytes)
    return client


# --- Unit Tests ---


@pytest.mark.unit
def test_should_download_audio_from_storage(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_storage: FakeStorageClient,
) -> None:
    generate_transcript(event, fake_backend, fake_storage)

    assert fake_storage.download_called_with == {
        "bucket": event.bucket,
        "key": event.key,
    }


@pytest.mark.unit
def test_should_call_backend_with_downloaded_bytes(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_storage: FakeStorageClient,
    audio_bytes: bytes,
) -> None:
    generate_transcript(event, fake_backend, fake_storage)

    assert len(fake_backend.calls) == 1
    assert fake_backend.calls[0] == audio_bytes


@pytest.mark.unit
def test_should_upload_transcript_to_storage(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_storage: FakeStorageClient,
) -> None:
    generate_transcript(event, fake_backend, fake_storage)

    assert fake_storage.upload_called_with is not None
    assert fake_storage.upload_called_with["bucket"] == "therapy-transcripts"
    assert fake_storage.upload_called_with["key"] == f"transcripts/{event.video_id}/transcript.txt"
    assert fake_storage.upload_called_with["content"] == fake_backend.transcript_text.encode("utf-8")


@pytest.mark.unit
def test_should_return_transcript_created_event_with_correct_metadata(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_storage: FakeStorageClient,
) -> None:
    result = generate_transcript(event, fake_backend, fake_storage)

    assert isinstance(result, TranscriptCreatedEvent)
    assert result.video_id == event.video_id
    assert result.bucket == "therapy-transcripts"
    assert result.key == f"transcripts/{event.video_id}/transcript.txt"

