import json
from pathlib import Path
from typing import Callable, Any

import pytest
import pika

from src.audio_extractor_service.rabbitmq_consumer import (
    RabbitMQConsumerConfig,
    RabbitMQVideoUploadedConsumer,
)
from tests.audio_extractor_service.conftest import FakeAudioEventPublisher


# --- Fixtures ---


@pytest.fixture
def config() -> RabbitMQConsumerConfig:
    return RabbitMQConsumerConfig(
        host="rabbitmq",
        port=5672,
        username="guest",
        password="guest",
        queue_name="video.uploaded",
    )


@pytest.fixture
def video_id() -> str:
    return "video-123"


@pytest.fixture
def base_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "data" / "audio"


@pytest.fixture
def message_body(video_id: str, filename: str, video_path: Path) -> bytes:
    return json.dumps({
        "video_id": video_id,
        "filename": filename,
        "storage_path": str(video_path),
    }).encode("utf-8")


@pytest.fixture
def mock_channel_with_callback(mocker):
    """Mock channel that captures the consume callback."""
    channel = mocker.MagicMock()
    channel._consume_callback = None

    def capture_basic_consume(queue, on_message_callback, auto_ack=False):
        channel._consume_callback = on_message_callback
        return "consumer-tag"

    channel.basic_consume.side_effect = capture_basic_consume
    return channel


@pytest.fixture
def mock_connection_with_callback(mocker, mock_channel_with_callback):
    """Mock connection that returns the callback-capturing channel."""
    connection = mocker.MagicMock()
    connection.channel.return_value = mock_channel_with_callback
    return connection


@pytest.fixture
def started_consumer(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    mock_channel_with_callback,
    mock_connection_with_callback,
    mocker,
) -> tuple[RabbitMQVideoUploadedConsumer, Any, Callable]:
    """Fixture that sets up and starts a consumer, returning the consumer, channel, and callback."""
    mocker.patch("pika.BlockingConnection", return_value=mock_connection_with_callback)
    mock_channel_with_callback.start_consuming.side_effect = KeyboardInterrupt

    consumer = RabbitMQVideoUploadedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    return consumer, mock_channel_with_callback, mock_channel_with_callback._consume_callback


# --- Tests ---


@pytest.mark.unit
def test_should_connect_with_correct_parameters(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    mocker,
    mock_connection,
    mock_channel,
):
    mock_blocking_connection = mocker.patch("pika.BlockingConnection", return_value=mock_connection)
    mock_channel.start_consuming.side_effect = KeyboardInterrupt

    consumer = RabbitMQVideoUploadedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    mock_blocking_connection.assert_called_once()
    call_args = mock_blocking_connection.call_args
    params = call_args[0][0]
    assert params.host == config.host
    assert params.port == config.port
    assert params.credentials.username == config.username
    assert params.credentials.password == config.password


@pytest.mark.unit
def test_should_declare_queue_durable(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    mocker,
    mock_connection,
    mock_channel,
):
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)
    mock_channel.start_consuming.side_effect = KeyboardInterrupt

    consumer = RabbitMQVideoUploadedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    mock_channel.queue_declare.assert_called_once_with(
        queue=config.queue_name,
        durable=True,
    )


@pytest.mark.unit
def test_should_process_message_and_create_audio_file(
    started_consumer: tuple,
    message_body: bytes,
    video_id: str,
    video_bytes: bytes,
    base_output_dir: Path,
    mocker,
):
    consumer, mock_channel, callback = started_consumer
    assert callback is not None

    fake_method = mocker.MagicMock()
    fake_method.delivery_tag = 42

    callback(mock_channel, fake_method, None, message_body)

    expected_audio_path = base_output_dir / video_id / "audio.mp3"
    assert expected_audio_path.is_file()
    contents = expected_audio_path.read_bytes()
    assert contents == video_bytes


@pytest.mark.unit
def test_should_publish_audio_extracted_event(
    started_consumer: tuple,
    fake_publisher: FakeAudioEventPublisher,
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
    (b'{"video_id": "v1"}', "missing storage_path"),
])
def test_should_handle_malformed_message_gracefully(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    mocker,
    mock_connection,
    mock_channel,
    invalid_body: bytes,
    description: str,
):
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)
    mock_channel.start_consuming.side_effect = KeyboardInterrupt

    captured_callback = {}
    def capture_basic_consume(queue, on_message_callback, auto_ack=False):
        captured_callback['callback'] = on_message_callback
        return "consumer-tag"
    mock_channel.basic_consume.side_effect = capture_basic_consume

    consumer = RabbitMQVideoUploadedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    callback = captured_callback.get('callback')
    assert callback is not None

    fake_method = mocker.MagicMock()
    fake_method.delivery_tag = 42

    try:
        callback(mock_channel, fake_method, None, invalid_body)
    except Exception:
        pass

    assert len(fake_publisher.published_events) == 0