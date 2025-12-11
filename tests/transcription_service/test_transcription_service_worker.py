import pytest

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.worker import process_audio_extracted_event
from tests.transcription_service.conftest import (
    FakeTranscriptionBackend,
    FakeTranscriptEventPublisher,
    FakeStorageClient,
)


# --- Unit Tests ---


@pytest.mark.unit
def test_should_call_backend_transcribe_once_with_downloaded_bytes(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    fake_storage: FakeStorageClient,
    audio_bytes: bytes,
) -> None:
    process_audio_extracted_event(event, fake_storage, fake_backend, fake_publisher)

    assert len(fake_backend.calls) == 1
    assert fake_backend.calls[0] == audio_bytes


@pytest.mark.unit
def test_should_return_transcript_created_event_with_correct_video_id(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    fake_storage: FakeStorageClient,
) -> None:
    result = process_audio_extracted_event(event, fake_storage, fake_backend, fake_publisher)

    assert result.video_id == event.video_id


@pytest.mark.unit
def test_should_upload_transcript_to_storage(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    fake_storage: FakeStorageClient,
) -> None:
    process_audio_extracted_event(event, fake_storage, fake_backend, fake_publisher)

    assert fake_storage.upload_called_with is not None
    assert fake_storage.upload_called_with["bucket"] == "therapy-transcripts"
    assert fake_storage.upload_called_with["key"] == f"transcripts/{event.video_id}/transcript.txt"


@pytest.mark.unit
def test_should_publish_exactly_one_event_equal_to_returned_event(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    fake_storage: FakeStorageClient,
) -> None:
    result = process_audio_extracted_event(event, fake_storage, fake_backend, fake_publisher)

    assert len(fake_publisher.published_events) == 1
    assert fake_publisher.published_events[0] == result

