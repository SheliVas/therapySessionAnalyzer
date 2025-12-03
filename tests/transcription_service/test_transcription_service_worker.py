from pathlib import Path

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.worker import process_audio_extracted_event
from tests.transcription_service.conftest import (
    FakeTranscriptionBackend,
    FakeTranscriptEventPublisher,
)


def test_should_call_backend_transcribe_once_with_correct_audio_path(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    base_output_dir: Path,
) -> None:
    process_audio_extracted_event(event, base_output_dir, fake_backend, fake_publisher)

    assert len(fake_backend.calls) == 1, f"expected 1 call, got {len(fake_backend.calls)}"
    expected_path = Path(event.audio_path)
    assert fake_backend.calls[0] == expected_path, (
        f"expected audio_path {expected_path}, got {fake_backend.calls[0]}"
    )


def test_should_return_transcript_created_event_with_correct_video_id(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    base_output_dir: Path,
) -> None:
    result = process_audio_extracted_event(event, base_output_dir, fake_backend, fake_publisher)

    assert result.video_id == event.video_id, (
        f"expected video_id {event.video_id}, got {result.video_id}"
    )


def test_should_return_transcript_path_pointing_to_existing_file(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    base_output_dir: Path,
) -> None:
    result = process_audio_extracted_event(event, base_output_dir, fake_backend, fake_publisher)

    expected_path = base_output_dir / event.video_id / "transcript.txt"
    assert Path(result.transcript_path) == expected_path, (
        f"expected transcript_path {expected_path}, got {result.transcript_path}"
    )
    assert expected_path.exists(), (
        f"expected transcript file to exist at {expected_path}, but it does not"
    )


def test_should_publish_exactly_one_event_equal_to_returned_event(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    base_output_dir: Path,
) -> None:
    result = process_audio_extracted_event(event, base_output_dir, fake_backend, fake_publisher)

    assert len(fake_publisher.published_events) == 1, (
        f"expected 1 published event, got {len(fake_publisher.published_events)}"
    )
    assert fake_publisher.published_events[0] == result, (
        f"expected published event {result}, got {fake_publisher.published_events[0]}"
    )
