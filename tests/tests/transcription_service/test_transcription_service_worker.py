from pathlib import Path

import pytest

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import (
    TranscriptCreatedEvent,
    TranscriptionBackend,
)
from src.transcription_service.worker import (
    TranscriptEventPublisher,
    process_audio_extracted_event,
)


class FakeTranscriptionBackend(TranscriptionBackend):
    def __init__(self, transcript_text: str) -> None:
        self.transcript_text = transcript_text
        self.calls: list[Path] = []

    def transcribe(self, audio_path: Path) -> str:
        self.calls.append(audio_path)
        return self.transcript_text


class FakeTranscriptEventPublisher(TranscriptEventPublisher):
    def __init__(self) -> None:
        self.published_events: list[TranscriptCreatedEvent] = []

    def publish_transcript_created(self, event: TranscriptCreatedEvent) -> None:
        self.published_events.append(event)


@pytest.fixture
def fake_audio_path(tmp_path: Path) -> Path:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_file = audio_dir / "audio.mp3"
    audio_file.write_bytes(b"fake audio content")
    return audio_file


@pytest.fixture
def event(fake_audio_path: Path) -> AudioExtractedEvent:
    return AudioExtractedEvent(
        video_id="video-123",
        audio_path=str(fake_audio_path),
    )


@pytest.fixture
def fake_backend() -> FakeTranscriptionBackend:
    return FakeTranscriptionBackend(transcript_text="hello transcript")


@pytest.fixture
def fake_publisher() -> FakeTranscriptEventPublisher:
    return FakeTranscriptEventPublisher()


@pytest.fixture
def base_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "data" / "transcripts"


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
