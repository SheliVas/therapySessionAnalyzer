import pytest

from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import AnalysisBackend, AnalysisResult, analyze_transcript


class FakeAnalysisBackend(AnalysisBackend):

    def __init__(self) -> None:
        self.calls: list[str] = []

    def analyze(self, transcript_text: str) -> AnalysisResult:
        self.calls.append(transcript_text)
        word_count = len(transcript_text.split())
        return AnalysisResult(
            video_id="video-123",
            word_count=word_count,
            extra={"backend": "fake"}
        )


@pytest.fixture
def fake_transcript_path(tmp_path) -> str:
    transcript_file = tmp_path / "transcript.txt"
    transcript_file.write_text("hello world hello")
    return str(transcript_file)


@pytest.fixture
def event(fake_transcript_path: str) -> TranscriptCreatedEvent:
    return TranscriptCreatedEvent(
        video_id="video-123",
        transcript_path=fake_transcript_path,
    )


@pytest.fixture
def fake_backend() -> FakeAnalysisBackend:
    return FakeAnalysisBackend()


def test_should_call_backend_analyze_once(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
) -> None:
    analyze_transcript(event, fake_backend)

    expected_calls = 1
    actual_calls = len(fake_backend.calls)
    assert actual_calls == expected_calls, f"expected {expected_calls} call, got {actual_calls}"

    expected_text = "hello world hello"
    actual_text = fake_backend.calls[0]
    assert actual_text == expected_text, f"expected transcript text '{expected_text}', got '{actual_text}'"


def test_should_return_analysis_result_with_video_id_matching_event(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
) -> None:
    result = analyze_transcript(event, fake_backend)

    expected_video_id = event.video_id
    actual_video_id = result.video_id
    assert actual_video_id == expected_video_id, f"expected video_id '{expected_video_id}', got '{actual_video_id}'"


def test_should_return_analysis_result_with_correct_word_count(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
) -> None:
    result = analyze_transcript(event, fake_backend)

    expected_word_count = 3
    actual_word_count = result.word_count
    assert actual_word_count == expected_word_count, f"expected word_count {expected_word_count}, got {actual_word_count}"


def test_should_return_analysis_result_with_correct_extra_data(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
) -> None:
    result = analyze_transcript(event, fake_backend)

    expected_extra = {"backend": "fake"}
    actual_extra = result.extra
    assert actual_extra == expected_extra, f"expected extra {expected_extra}, got {actual_extra}"