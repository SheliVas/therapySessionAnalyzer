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
    fake_videos_repository,
) -> None:
    from src.transcription_service.domain import generate_transcript
    generate_transcript(event, fake_backend, fake_storage, fake_videos_repository)

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
    fake_videos_repository,
) -> None:
    from src.transcription_service.domain import generate_transcript
    generate_transcript(event, fake_backend, fake_storage, fake_videos_repository)

    assert len(fake_backend.calls) == 1
    assert fake_backend.calls[0] == audio_bytes


@pytest.mark.unit
def test_should_upload_transcript_to_storage(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_storage: FakeStorageClient,
    fake_videos_repository,
) -> None:
    from src.transcription_service.domain import generate_transcript
    generate_transcript(event, fake_backend, fake_storage, fake_videos_repository)

    assert fake_storage.upload_called_with is not None
    assert fake_storage.upload_called_with["bucket"] == "therapy-transcripts"
    assert fake_storage.upload_called_with["key"] == f"transcripts/{event.video_id}/transcript.txt"
    assert fake_storage.upload_called_with["content"] == fake_backend.transcript_text.encode("utf-8")


@pytest.mark.unit
def test_should_return_transcript_created_event_with_correct_metadata(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_storage: FakeStorageClient,
    fake_videos_repository,
) -> None:
    from src.transcription_service.domain import generate_transcript
    result = generate_transcript(event, fake_backend, fake_storage, fake_videos_repository)

    assert isinstance(result, TranscriptCreatedEvent)
    assert result.video_id == event.video_id
    assert result.bucket == "therapy-transcripts"
    assert result.key == f"transcripts/{event.video_id}/transcript.txt"


@pytest.mark.unit
def test_should_call_repository_mark_transcribed_with_correct_path(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_storage: FakeStorageClient,
    fake_videos_repository,
) -> None:
    from src.transcription_service.domain import generate_transcript
    generate_transcript(event, fake_backend, fake_storage, fake_videos_repository)
    
    assert len(fake_videos_repository.mark_transcribed_calls) == 1
    call = fake_videos_repository.mark_transcribed_calls[0]
    assert call["video_id"] == event.video_id
    assert "therapy-transcripts" in call["transcript_path"]
    assert "transcript.txt" in call["transcript_path"]


@pytest.mark.unit
def test_should_not_publish_on_repository_failure(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_storage: FakeStorageClient,
    fake_videos_repository,
    fake_publisher,
) -> None:
    from src.transcription_service.domain import generate_transcript
    from src.transcription_service.worker import process_audio_extracted_event
    
    fake_videos_repository.should_raise_error = True
    
    with pytest.raises(ValueError, match="Repository error"):
        process_audio_extracted_event(
            event=event,
            storage_client=fake_storage,
            backend=fake_backend,
            repository=fake_videos_repository,
            publisher=fake_publisher,
        )
    
    assert len(fake_publisher.published_events) == 0
