"""Tests for RabbitMQTranscriptCreatedConsumer dependency injection."""
import pytest

from src.analysis_service.rabbitmq_consumer import RabbitMQTranscriptCreatedConsumer, RabbitMQConsumerConfig
from tests.analysis_service.conftest import (
    FakeAnalysisBackend,
    FakeAnalysisEventPublisher,
    FakeAnalysisRepository,
    FakeStorageClient,
)


# --- Fixtures ---

@pytest.fixture
def consumer_config() -> RabbitMQConsumerConfig:
    """Basic consumer config for testing."""
    return RabbitMQConsumerConfig(
        host="rabbitmq",
        port=5672,
        username="guest",
        password="guest",
        queue_name="transcript.created",
    )


@pytest.fixture
def fake_videos_repository_for_consumer():
    """Fake VideosRepository for consumer tests."""
    from tests.conftest import FakeVideosRepository
    return FakeVideosRepository()


# --- Unit Tests ---

@pytest.mark.unit
def test_should_accept_storage_client_and_pass_to_process_event(
    consumer_config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_storage_client: FakeStorageClient,
    fake_videos_repository_for_consumer,
) -> None:
    """Verify RabbitMQTranscriptCreatedConsumer accepts and passes storage_client."""
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=consumer_config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
        storage_client=fake_storage_client,
        videos_repository=fake_videos_repository_for_consumer,
    )

    assert consumer._storage_client is fake_storage_client


@pytest.mark.unit
def test_should_accept_videos_repository_and_pass_to_process_event(
    consumer_config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_storage_client: FakeStorageClient,
    fake_videos_repository_for_consumer,
) -> None:
    """Verify RabbitMQTranscriptCreatedConsumer accepts and stores videos_repository."""
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=consumer_config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
        storage_client=fake_storage_client,
        videos_repository=fake_videos_repository_for_consumer,
    )

    assert consumer._videos_repository is fake_videos_repository_for_consumer
