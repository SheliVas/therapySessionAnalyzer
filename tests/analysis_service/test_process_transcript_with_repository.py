"""Tests for process_transcript_created_event with VideosRepository integration."""
import pytest

from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.worker import process_transcript_created_event
from tests.analysis_service.conftest import (
    FakeAnalysisBackend,
    FakeAnalysisEventPublisher,
    FakeAnalysisRepository,
)
from tests.fakes import FakeStorageClient, FakeVideosRepository


# --- Fixtures ---

@pytest.fixture
def fake_videos_repository_for_analysis():
    """Fake VideosRepository for analysis_service tests."""
    return FakeVideosRepository()



# --- Unit Tests ---

@pytest.mark.unit
def test_should_call_mark_analyzed_with_video_id_and_word_count(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_storage_client: FakeStorageClient,
    fake_videos_repository_for_analysis,
) -> None:
    """Verify process_transcript_created_event calls repository.mark_analyzed with correct args."""
    process_transcript_created_event(
        event,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
        storage_client=fake_storage_client,
        videos_repository=fake_videos_repository_for_analysis,
    )

    expected_calls = 1
    actual_calls = len(fake_videos_repository_for_analysis.mark_analyzed_calls)
    assert actual_calls == expected_calls

    call_args = fake_videos_repository_for_analysis.mark_analyzed_calls[0]
    assert call_args["video_id"] == event.video_id
    assert call_args["word_count"] == 3  # "hello world hello" = 3 words


@pytest.mark.unit
def test_should_not_publish_when_mark_analyzed_raises_error(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_storage_client: FakeStorageClient,
    fake_videos_repository_for_analysis,
) -> None:
    """Verify that failures in mark_analyzed prevent publishing."""
    fake_videos_repository_for_analysis.should_raise_error = True

    with pytest.raises(ValueError, match="Repository error"):
        process_transcript_created_event(
            event,
            backend=fake_backend,
            publisher=fake_publisher,
            repository=fake_repository,
            storage_client=fake_storage_client,
            videos_repository=fake_videos_repository_for_analysis,
        )

    expected_published_count = 0
    actual_published_count = len(fake_publisher.published_events)
    assert actual_published_count == expected_published_count


@pytest.mark.unit
def test_should_call_mark_analyzed_before_publishing(
    event: TranscriptCreatedEvent,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_storage_client: FakeStorageClient,
    fake_videos_repository_for_analysis,
) -> None:
    """Verify mark_analyzed is called before publishing event."""

    class OrderTrackingPublisher(FakeAnalysisEventPublisher):
        def __init__(self, videos_repo):
            super().__init__()
            self.videos_repo = videos_repo
            self.call_order = []

        def publish_analysis_completed(self, event):
            self.call_order.append("publish")
            super().publish_analysis_completed(event)

    class OrderTrackingVideosRepository:
        def __init__(self):
            self.call_order = []
            self.mark_analyzed_calls = []

        def mark_analyzed(self, video_id: str, word_count: int) -> None:
            self.call_order.append("mark_analyzed")
            self.mark_analyzed_calls.append({
                "video_id": video_id,
                "word_count": word_count,
            })

    tracking_repo = OrderTrackingVideosRepository()
    tracking_publisher = OrderTrackingPublisher(tracking_repo)

    process_transcript_created_event(
        event,
        backend=fake_backend,
        publisher=tracking_publisher,
        repository=fake_repository,
        storage_client=fake_storage_client,
        videos_repository=tracking_repo,
    )

    assert tracking_repo.call_order[0] == "mark_analyzed"
    assert tracking_publisher.call_order[0] == "publish"
