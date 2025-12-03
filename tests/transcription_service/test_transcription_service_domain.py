"""Tests for transcription_service domain logic."""
from pathlib import Path

import pytest

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import (
    TranscriptCreatedEvent,
    TranscriptionBackend,
    generate_transcript,
)


class FakeTranscriptionBackend(TranscriptionBackend):
    """Fake backend that records calls and returns a fixed transcript."""

    def __init__(self, transcript_text: str) -> None:
        self.transcript_text = transcript_text
        self.calls: list[Path] = []

    def transcribe(self, audio_path: Path) -> str:
        self.calls.append(audio_path)
        return self.transcript_text


@pytest.fixture
def fake_audio_path(tmp_path: Path) -> Path:
    """Create a fake audio file and return its path."""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_file = audio_dir / "audio.mp3"
    audio_file.write_bytes(b"fake audio content")
    return audio_file


@pytest.fixture
def event(fake_audio_path: Path) -> AudioExtractedEvent:
    """Create an AudioExtractedEvent for testing."""
    return AudioExtractedEvent(
        video_id="video-123",
        audio_path=str(fake_audio_path),
    )


@pytest.fixture
def fake_backend() -> FakeTranscriptionBackend:
    """Create a fake transcription backend."""
    return FakeTranscriptionBackend(transcript_text="hello world transcript")


@pytest.fixture
def base_output_dir(tmp_path: Path) -> Path:
    """Return the base output directory for transcripts."""
    return tmp_path / "data" / "transcripts"


def test_should_call_backend_once_with_correct_audio_path_when_event_received(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    base_output_dir: Path,
) -> None:
    """Backend should be called exactly once with the audio path from the event."""
    generate_transcript(event, fake_backend, base_output_dir)

    assert len(fake_backend.calls) == 1, f"expected 1 call, got {len(fake_backend.calls)}"
    expected_path = Path(event.audio_path)
    assert fake_backend.calls[0] == expected_path, (
        f"expected audio_path {expected_path}, got {fake_backend.calls[0]}"
    )


def test_should_return_transcript_created_event_with_correct_video_id(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    base_output_dir: Path,
) -> None:
    """Returned event should have the same video_id as the input event."""
    result = generate_transcript(event, fake_backend, base_output_dir)

    assert result.video_id == event.video_id, (
        f"expected video_id {event.video_id}, got {result.video_id}"
    )


def test_should_return_transcript_path_pointing_to_existing_file(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    base_output_dir: Path,
) -> None:
    """Returned event should have a transcript_path that points to an existing file."""
    result = generate_transcript(event, fake_backend, base_output_dir)

    transcript_file = Path(result.transcript_path)
    assert transcript_file.exists(), (
        f"expected transcript file to exist at {result.transcript_path}, but it does not"
    )


def test_should_create_transcript_file_in_correct_location(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    base_output_dir: Path,
) -> None:
    """Transcript file should be at base_output_dir / video_id / transcript.txt."""
    result = generate_transcript(event, fake_backend, base_output_dir)

    expected_path = base_output_dir / event.video_id / "transcript.txt"
    assert Path(result.transcript_path) == expected_path, (
        f"expected transcript_path {expected_path}, got {result.transcript_path}"
    )
    assert expected_path.exists(), (
        f"expected transcript file to exist at {expected_path}, but it does not"
    )


def test_should_write_correct_transcript_content_to_file(
    event: AudioExtractedEvent,
    fake_backend: FakeTranscriptionBackend,
    base_output_dir: Path,
) -> None:
    """Transcript file should contain the text returned by the backend."""
    result = generate_transcript(event, fake_backend, base_output_dir)

    transcript_file = Path(result.transcript_path)
    actual_content = transcript_file.read_text()
    expected_content = fake_backend.transcript_text
    assert actual_content == expected_content, (
        f"expected file content '{expected_content}', got '{actual_content}'"
    )
