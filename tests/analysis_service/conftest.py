import pytest
from pathlib import Path
from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import AnalysisBackend, AnalysisResult
from src.analysis_service.worker import (
    AnalysisCompletedEvent,
    AnalysisEventPublisher,
    AnalysisRepository,
)


class FakeAnalysisBackend(AnalysisBackend):
    def __init__(self, video_id: str = "video-123") -> None:
        self.video_id = video_id
        self.calls: list[str] = []

    def analyze(self, transcript_text: str) -> AnalysisResult:
        self.calls.append(transcript_text)
        word_count = len(transcript_text.split())
        return AnalysisResult(
            video_id=self.video_id,
            word_count=word_count,
            extra={"backend": "fake"}
        )


class FakeAnalysisEventPublisher(AnalysisEventPublisher):
    def __init__(self) -> None:
        self.published_events: list[AnalysisCompletedEvent] = []

    def publish_analysis_completed(self, event: AnalysisCompletedEvent) -> None:
        self.published_events.append(event)


class FakeAnalysisRepository(AnalysisRepository):
    def __init__(self) -> None:
        self.saved_events: list[AnalysisCompletedEvent] = []

    def save_analysis(self, event: AnalysisCompletedEvent) -> None:
        self.saved_events.append(event)


@pytest.fixture
def fake_transcript_path(tmp_path: Path) -> str:
    transcript_file = tmp_path / "transcript.txt"
    transcript_file.write_text("hello world hello")
    return str(transcript_file)


@pytest.fixture
def video_id() -> str:
    return "video-123"


@pytest.fixture
def event(fake_transcript_path: str, video_id: str) -> TranscriptCreatedEvent:
    return TranscriptCreatedEvent(
        video_id=video_id,
        transcript_path=fake_transcript_path,
    )


@pytest.fixture
def fake_backend(video_id: str) -> FakeAnalysisBackend:
    return FakeAnalysisBackend(video_id=video_id)


@pytest.fixture
def fake_publisher() -> FakeAnalysisEventPublisher:
    return FakeAnalysisEventPublisher()


@pytest.fixture
def fake_repository() -> FakeAnalysisRepository:
    return FakeAnalysisRepository()
