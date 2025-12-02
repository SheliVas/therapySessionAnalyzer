import pytest
from pathlib import Path

from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import AnalysisBackend, AnalysisResult, analyze_transcript
from src.analysis_service.worker import (
    AnalysisCompletedEvent,
    AnalysisEventPublisher,
    process_transcript_created_event,
)


class FakeAnalysisBackend(AnalysisBackend):

    def __init__(self, video_id: str) -> None:
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


def test_should_call_backend_analyze_once(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
) -> None:
    process_transcript_created_event(event, fake_backend, fake_publisher)

    expected_calls = 1
    actual_calls = len(fake_backend.calls)
    assert actual_calls == expected_calls, f"expected {expected_calls} call, got {actual_calls}"

    expected_text = "hello world hello"
    actual_text = fake_backend.calls[0]
    assert actual_text == expected_text, f"expected transcript text '{expected_text}', got '{actual_text}'"


def test_should_return_analysis_completed_event_with_video_id_matching_event(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
) -> None:
    result = process_transcript_created_event(event, fake_backend, fake_publisher)

    expected_video_id = event.video_id
    actual_video_id = result.video_id
    assert actual_video_id == expected_video_id, f"expected video_id '{expected_video_id}', got '{actual_video_id}'"


def test_should_return_analysis_completed_event_with_correct_word_count(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
) -> None:
    result = process_transcript_created_event(event, fake_backend, fake_publisher)

    expected_word_count = 3
    actual_word_count = result.word_count
    assert actual_word_count == expected_word_count, f"expected word_count {expected_word_count}, got {actual_word_count}"


def test_should_return_analysis_completed_event_with_correct_extra_data(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
) -> None:
    result = process_transcript_created_event(event, fake_backend, fake_publisher)

    expected_extra = {"backend": "fake"}
    actual_extra = result.extra
    assert actual_extra == expected_extra, f"expected extra {expected_extra}, got {actual_extra}"


def test_should_publish_exactly_one_event_equal_to_returned_event(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
) -> None:
    result = process_transcript_created_event(event, fake_backend, fake_publisher)

    expected_count = 1
    actual_count = len(fake_publisher.published_events)
    assert actual_count == expected_count, f"expected {expected_count} published event, got {actual_count}"

    expected_event = result
    actual_event = fake_publisher.published_events[0]
    assert actual_event == expected_event, f"expected published event {expected_event}, got {actual_event}"
