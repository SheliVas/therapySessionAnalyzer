import pytest
import mongomock

from src.analysis_service.worker import AnalysisCompletedEvent
from src.analysis_service.mongo_repository import MongoAnalysisRepository


@pytest.fixture
def mongo_client() -> mongomock.MongoClient:
    return mongomock.MongoClient()


@pytest.fixture
def repository(mongo_client: mongomock.MongoClient) -> MongoAnalysisRepository:
    return MongoAnalysisRepository(client=mongo_client)


@pytest.fixture
def sample_event() -> AnalysisCompletedEvent:
    return AnalysisCompletedEvent(
        video_id="video-123",
        word_count=42,
        extra={"foo": "bar"},
    )


class TestMongoAnalysisRepository:

    def test_should_save_and_retrieve_event_when_event_exists(
        self,
        repository: MongoAnalysisRepository,
        sample_event: AnalysisCompletedEvent,
    ) -> None:
        repository.save_analysis(sample_event)
        result = repository.get_analysis("video-123")

        assert result is not None, "expected event to be found, got None"
        assert result.video_id == sample_event.video_id, (
            f"expected video_id {sample_event.video_id}, got {result.video_id}"
        )
        assert result.word_count == sample_event.word_count, (
            f"expected word_count {sample_event.word_count}, got {result.word_count}"
        )
        assert result.extra == {"foo": "bar"}, (
            f"expected extra {{'foo': 'bar'}}, got {result.extra}"
        )

    def test_should_return_none_when_event_not_found(
        self,
        repository: MongoAnalysisRepository,
    ) -> None:
        result = repository.get_analysis("missing-id")

        assert result is None, f"expected None for missing video_id, got {result}"

    def test_should_upsert_event_when_saving_same_video_id_twice(
        self,
        repository: MongoAnalysisRepository,
        mongo_client: mongomock.MongoClient,
    ) -> None:
        event_v1 = AnalysisCompletedEvent(
            video_id="video-123",
            word_count=10,
            extra={"version": 1},
        )
        event_v2 = AnalysisCompletedEvent(
            video_id="video-123",
            word_count=99,
            extra={"version": 2},
        )

        repository.save_analysis(event_v1)
        repository.save_analysis(event_v2)
        result = repository.get_analysis("video-123")

        collection = mongo_client["therapy_analysis"]["analysis_results"]
        doc_count = collection.count_documents({"video_id": "video-123"})
        assert doc_count == 1, f"expected 1 document after upsert, got {doc_count}"
        assert result is not None, "expected event to be found, got None"
        assert result.word_count == 99, f"expected word_count 99, got {result.word_count}"
        assert result.extra == {"version": 2}, (
            f"expected extra {{'version': 2}}, got {result.extra}"
        )
