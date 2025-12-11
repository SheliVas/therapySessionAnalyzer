import json
from pathlib import Path
from typing import Callable, Any

import pytest
import pika

from src.analysis_service.rabbitmq_consumer import (
    RabbitMQConsumerConfig,
    RabbitMQTranscriptCreatedConsumer,
)
from tests.analysis_service.conftest import (
    FakeAnalysisBackend,
    FakeAnalysisEventPublisher,
    FakeAnalysisRepository,
    FakeStorageClient,
)


# --- Fixtures ---


@pytest.fixture
def config() -> RabbitMQConsumerConfig:
    return RabbitMQConsumerConfig(
        host="rabbitmq",
        port=5672,
        username="guest",
        password="guest",
        queue_name="transcript.created",
    )


@pytest.fixture
def transcript_text() -> str:
    return "hello world hello"


@pytest.fixture
def message_body(video_id: str) -> bytes:
    return json.dumps({
        "video_id": video_id,
        "bucket": "therapy-transcripts",
        "key": f"transcripts/{video_id}/transcript.txt",
    }).encode("utf-8")


@pytest.fixture
def mock_channel(mocker):
    channel = mocker.MagicMock()
    channel._consume_callback = None

    def capture_basic_consume(queue, on_message_callback, auto_ack=False):
        channel._consume_callback = on_message_callback
        return "consumer-tag"

    channel.basic_consume.side_effect = capture_basic_consume
    return channel


@pytest.fixture
def mock_connection(mocker, mock_channel):
    connection = mocker.MagicMock()
    connection.channel.return_value = mock_channel
    return connection


@pytest.fixture
def mock_pika(mocker, mock_connection):
    return mocker.patch("pika.BlockingConnection", return_value=mock_connection)


@pytest.fixture
def started_consumer(
    config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_storage_client: FakeStorageClient,
    mock_channel,
    mock_pika,
) -> tuple[RabbitMQTranscriptCreatedConsumer, Any, Callable]:
    """Fixture that sets up and starts a consumer, returning the consumer, channel, and callback."""
    mock_channel.start_consuming.side_effect = KeyboardInterrupt
    
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
        storage_client=fake_storage_client,
    )
    
    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass
    
    return consumer, mock_channel, mock_channel._consume_callback


# --- Unit Tests ---


@pytest.mark.unit
def test_should_connect_with_correct_parameters(
    config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_storage_client: FakeStorageClient,
    mock_channel,
    mock_pika,
):
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
        storage_client=fake_storage_client,
    )

    mock_channel.start_consuming.side_effect = KeyboardInterrupt

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    mock_pika.assert_called_once()
    params = mock_pika.call_args[0][0]
    assert params.host == config.host
    assert params.port == config.port
    assert params.credentials.username == config.username
    assert params.credentials.password == config.password


@pytest.mark.unit
def test_should_declare_queue_durable(
    config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_storage_client: FakeStorageClient,
    mock_channel,
    mock_pika,
):
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
        storage_client=fake_storage_client,
    )

    mock_channel.start_consuming.side_effect = KeyboardInterrupt

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    mock_channel.queue_declare.assert_called_once_with(
        queue=config.queue_name,
        durable=True,
    )


@pytest.mark.unit
def test_should_process_message_and_call_backend(
    started_consumer: tuple,
    fake_backend: FakeAnalysisBackend,
    message_body: bytes,
    transcript_text: str,
    mocker,
):
    consumer, mock_channel, callback = started_consumer
    assert callback is not None

    fake_method = mocker.MagicMock()
    fake_method.delivery_tag = 42

    callback(mock_channel, fake_method, None, message_body)

    assert len(fake_backend.calls) == 1
    assert fake_backend.calls[0] == transcript_text


@pytest.mark.unit
def test_should_save_exactly_one_event_after_processing(
    started_consumer: tuple,
    fake_repository: FakeAnalysisRepository,
    message_body: bytes,
    video_id: str,
    mocker,
):
    consumer, mock_channel, callback = started_consumer
    assert callback is not None

    fake_method = mocker.MagicMock()
    fake_method.delivery_tag = 42

    callback(mock_channel, fake_method, None, message_body)

    assert len(fake_repository.saved_events) == 1
    event = fake_repository.saved_events[0]
    assert event.video_id == video_id
    assert event.word_count == 3


@pytest.mark.unit
def test_should_publish_exactly_one_event_after_processing(
    started_consumer: tuple,
    fake_publisher: FakeAnalysisEventPublisher,
    message_body: bytes,
    video_id: str,
    mocker,
):

    consumer, mock_channel, callback = started_consumer
    assert callback is not None

    fake_method = mocker.MagicMock()
    fake_method.delivery_tag = 42

    callback(mock_channel, fake_method, None, message_body)

    assert len(fake_publisher.published_events) == 1
    event = fake_publisher.published_events[0]
    assert event.video_id == video_id


@pytest.mark.unit
def test_should_acknowledge_message_after_processing(
    started_consumer: tuple,
    message_body: bytes,
    mocker,
):
    consumer, mock_channel, callback = started_consumer
    assert callback is not None

    fake_method = mocker.MagicMock()
    fake_method.delivery_tag = 42

    callback(mock_channel, fake_method, None, message_body)

    mock_channel.basic_ack.assert_called_once_with(delivery_tag=42)



@pytest.mark.unit
@pytest.mark.parametrize("invalid_body,description", [
    (b"not-json", "non-JSON body"),
    (b'{"video_id": null}', "null video_id"),
    (b'{}', "empty JSON object"),
    (b'{"video_id": "v1"}', "missing bucket"),
])
def test_should_handle_malformed_message_gracefully(
    config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_storage_client: FakeStorageClient,
    mock_channel,
    mock_pika,
    invalid_body: bytes,
    description: str,
    mocker,
):
    mock_channel.start_consuming.side_effect = KeyboardInterrupt
    
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
        storage_client=fake_storage_client,
    )
    
    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass
    
    callback = mock_channel._consume_callback
    assert callback is not None
    
    fake_method = mocker.MagicMock()
    fake_method.delivery_tag = 42

    try:
        callback(mock_channel, fake_method, None, invalid_body)
    except Exception as e:
        pass
    
    assert len(fake_publisher.published_events) == 0
