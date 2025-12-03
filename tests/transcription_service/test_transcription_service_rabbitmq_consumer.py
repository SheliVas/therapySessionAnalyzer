import json
from pathlib import Path
from typing import Callable, Any

import pika
import pytest

from src.transcription_service.rabbitmq_consumer import (
    RabbitMQConsumerConfig,
    RabbitMQAudioExtractedConsumer,
)
from tests.transcription_service.conftest import FakeTranscriptionBackend, FakeTranscriptEventPublisher


# --- Fixtures ---


@pytest.fixture
def config() -> RabbitMQConsumerConfig:
    return RabbitMQConsumerConfig(
        host="rabbitmq",
        port=5672,
        username="guest",
        password="guest",
        queue_name="audio.extracted",
    )


@pytest.fixture
def video_id() -> str:
    return "video-123"


@pytest.fixture
def audio_bytes() -> bytes:
    return b"fake-audio-content"


@pytest.fixture
def audio_path(tmp_path: Path, audio_bytes: bytes) -> Path:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_file = audio_dir / "audio.mp3"
    audio_file.write_bytes(audio_bytes)
    return audio_file


@pytest.fixture
def message_body(video_id: str, audio_path: Path) -> bytes:
    return json.dumps({
        "video_id": video_id,
        "audio_path": str(audio_path),
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
    base_output_dir: Path,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    mock_channel,
    mock_pika,
) -> tuple[RabbitMQAudioExtractedConsumer, Any, Callable]:
    mock_channel.start_consuming.side_effect = KeyboardInterrupt
    
    consumer = RabbitMQAudioExtractedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        backend=fake_backend,
        publisher=fake_publisher,
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
    base_output_dir: Path,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    mock_channel,
    mock_pika,
) -> None:
    consumer = RabbitMQAudioExtractedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        backend=fake_backend,
        publisher=fake_publisher,
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
    base_output_dir: Path,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    mock_channel,
    mock_pika,
) -> None:
    consumer = RabbitMQAudioExtractedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        backend=fake_backend,
        publisher=fake_publisher,
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
def test_should_process_message_and_create_transcript_file(
    started_consumer: tuple,
    fake_backend: FakeTranscriptionBackend,
    message_body: bytes,
    video_id: str,
    base_output_dir: Path,
    mocker,
) -> None:
    consumer, mock_channel, callback = started_consumer
    assert callback is not None

    fake_method = mocker.MagicMock()
    fake_method.delivery_tag = 42

    callback(mock_channel, fake_method, None, message_body)

    expected_transcript_path = base_output_dir / video_id / "transcript.txt"
    assert expected_transcript_path.is_file()

    contents = expected_transcript_path.read_text()
    assert contents == fake_backend.transcript_text


@pytest.mark.unit
def test_should_call_backend_with_correct_audio_path(
    started_consumer: tuple,
    fake_backend: FakeTranscriptionBackend,
    message_body: bytes,
    audio_path: Path,
    mocker,
) -> None:

    consumer, mock_channel, callback = started_consumer
    assert callback is not None

    fake_method = mocker.MagicMock()
    fake_method.delivery_tag = 42

    callback(mock_channel, fake_method, None, message_body)

    assert len(fake_backend.calls) == 1
    assert fake_backend.calls[0] == audio_path


@pytest.mark.unit
def test_should_publish_transcript_created_event(
    started_consumer: tuple,
    fake_publisher: FakeTranscriptEventPublisher,
    message_body: bytes,
    video_id: str,
    mocker,
) -> None:
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
) -> None:
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
    (b'{"video_id": "v1"}', "missing audio_path"),
])
def test_should_handle_malformed_message_gracefully(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    mock_channel,
    mock_pika,
    invalid_body: bytes,
    description: str,
    mocker,
) -> None:
    mock_channel.start_consuming.side_effect = KeyboardInterrupt
    
    consumer = RabbitMQAudioExtractedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        backend=fake_backend,
        publisher=fake_publisher,
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
