import pytest
from pathlib import Path
from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import (
    TranscriptCreatedEvent,
    TranscriptionBackend,
)
from src.transcription_service.worker import TranscriptEventPublisher


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
