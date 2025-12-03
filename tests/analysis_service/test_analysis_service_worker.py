from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.worker import process_transcript_created_event
from tests.analysis_service.conftest import (
    FakeAnalysisBackend,
    FakeAnalysisEventPublisher,
    FakeAnalysisRepository,
)


def test_should_call_backend_analyze_once(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
) -> None:
    process_transcript_created_event(event, fake_backend, fake_publisher, fake_repository)

    expected_calls = 1
    actual_calls = len(fake_backend.calls)
    assert actual_calls == expected_calls

    expected_text = "hello world hello"
    actual_text = fake_backend.calls[0]
    assert actual_text == expected_text


def test_should_return_analysis_completed_event_with_video_id_matching_event(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
) -> None:
    result = process_transcript_created_event(event, fake_backend, fake_publisher, fake_repository)

    expected_video_id = event.video_id
    actual_video_id = result.video_id
    assert actual_video_id == expected_video_id


def test_should_return_analysis_completed_event_with_correct_word_count(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
) -> None:
    result = process_transcript_created_event(event, fake_backend, fake_publisher, fake_repository)

    expected_word_count = 3
    actual_word_count = result.word_count
    assert actual_word_count == expected_word_count


def test_should_return_analysis_completed_event_with_correct_extra_data(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
) -> None:
    result = process_transcript_created_event(event, fake_backend, fake_publisher, fake_repository)

    expected_extra = {"backend": "fake"}
    actual_extra = result.extra
    assert actual_extra == expected_extra


def test_should_publish_exactly_one_event_equal_to_returned_event(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
) -> None:
    result = process_transcript_created_event(event, fake_backend, fake_publisher, fake_repository)

    expected_count = 1
    actual_count = len(fake_publisher.published_events)
    assert actual_count == expected_count

    expected_event = result
    actual_event = fake_publisher.published_events[0]
    assert actual_event == expected_event


def test_should_save_exactly_one_event_equal_to_returned_event(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
) -> None:
    result = process_transcript_created_event(event, fake_backend, fake_publisher, fake_repository)

    expected_count = 1
    actual_count = len(fake_repository.saved_events)
    assert actual_count == expected_count

    expected_event = result
    actual_event = fake_repository.saved_events[0]
    assert actual_event == expected_event
