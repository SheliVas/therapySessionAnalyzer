from pathlib import Path

import pytest

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.worker import process_audio_extracted_event
from tests.transcription_service.conftest import (
    FakeTranscriptionBackend,
    FakeTranscriptEventPublisher,
)


# --- Unit Tests ---


@pytest.mark.unit
def test_should_call_backend_transcribe_once_with_correct_audio_path(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    base_output_dir: Path,
) -> None:
    process_audio_extracted_event(event, base_output_dir, fake_backend, fake_publisher)

    assert len(fake_backend.calls) == 1
    expected_path = Path(event.audio_path)
    assert fake_backend.calls[0] == expected_path


@pytest.mark.unit
def test_should_return_transcript_created_event_with_correct_video_id(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    base_output_dir: Path,
) -> None:
    result = process_audio_extracted_event(event, base_output_dir, fake_backend, fake_publisher)

    assert result.video_id == event.video_id


@pytest.mark.unit
def test_should_return_transcript_path_pointing_to_existing_file(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    base_output_dir: Path,
) -> None:
    result = process_audio_extracted_event(event, base_output_dir, fake_backend, fake_publisher)

    expected_path = base_output_dir / event.video_id / "transcript.txt"
    assert Path(result.transcript_path) == expected_path
    assert expected_path.exists()


@pytest.mark.unit
def test_should_publish_exactly_one_event_equal_to_returned_event(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    base_output_dir: Path,
) -> None:
    result = process_audio_extracted_event(event, base_output_dir, fake_backend, fake_publisher)

    assert len(fake_publisher.published_events) == 1
    assert fake_publisher.published_events[0] == result
