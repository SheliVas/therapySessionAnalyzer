import json
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock

import pytest
import pika

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.audio_extractor_service.rabbitmq_consumer import (
    RabbitMQConsumerConfig,
    RabbitMQVideoUploadedConsumer,
)


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
def video_bytes() -> bytes:
    return b"fake-video-content"


@pytest.fixture
def video_id() -> str:
    return "video-123"


@pytest.fixture
def filename() -> str:
    return "session.mp4"


@pytest.fixture
def video_path(tmp_path: Path, filename: str, video_bytes: bytes) -> Path:
    path = tmp_path / filename
    path.write_bytes(video_bytes)
    return path


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


class FakeAudioEventPublisher:
    def __init__(self) -> None:
        self.published_events: list[AudioExtractedEvent] = []

    def publish_audio_extracted(self, event: AudioExtractedEvent) -> None:
        self.published_events.append(event)


@pytest.fixture
def fake_publisher() -> FakeAudioEventPublisher:
    return FakeAudioEventPublisher()


@pytest.fixture
def fake_channel() -> MagicMock:
    channel = MagicMock()
    channel._consume_callback: Callable | None = None

    def capture_basic_consume(queue, on_message_callback, auto_ack=False):
        channel._consume_callback = on_message_callback
        return "consumer-tag"

    channel.basic_consume.side_effect = capture_basic_consume
    return channel


@pytest.fixture
def fake_connection(fake_channel: MagicMock) -> MagicMock:
    connection = MagicMock()
    connection.channel.return_value = fake_channel
    return connection


@pytest.fixture
def mock_pika(monkeypatch, fake_connection: MagicMock) -> list[pika.ConnectionParameters]:
    captured_params: list[pika.ConnectionParameters] = []

    def fake_blocking_connection(params):
        captured_params.append(params)
        return fake_connection

    monkeypatch.setattr(pika, "BlockingConnection", fake_blocking_connection)
    return captured_params


# --- Tests ---


def test_should_connect_with_correct_parameters(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
):
    consumer = RabbitMQVideoUploadedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    # Start consuming, capture callback, then stop
    fake_channel.start_consuming.side_effect = KeyboardInterrupt

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    assert len(mock_pika) == 1, f"expected 1 connection attempt, got {len(mock_pika)}"
    params = mock_pika[0]
    assert params.host == config.host, f"expected host {config.host}, got {params.host}"
    assert params.port == config.port, f"expected port {config.port}, got {params.port}"
    assert params.credentials.username == config.username, f"expected username {config.username}, got {params.credentials.username}"
    assert params.credentials.password == config.password, f"expected password {config.password}, got {params.credentials.password}"


def test_should_declare_queue_durable(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
):
    consumer = RabbitMQVideoUploadedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )
    # Start consuming, capture callback, then stop
    fake_channel.start_consuming.side_effect = KeyboardInterrupt

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    fake_channel.queue_declare.assert_called_once_with(
        queue=config.queue_name,
        durable=True,
    ), f"expected queue_declare called with queue={config.queue_name} and durable=True"


def test_should_process_message_and_create_audio_file(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
    video_id: str,
    video_bytes: bytes,
):
    consumer = RabbitMQVideoUploadedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    # Start consuming, capture callback, then stop
    fake_channel.start_consuming.side_effect = KeyboardInterrupt

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    callback = fake_channel._consume_callback
    assert callback is not None, "basic_consume callback was not registered"

    fake_method = MagicMock()
    fake_method.delivery_tag = 42

    callback(fake_channel, fake_method, None, message_body)

    expected_audio_path = base_output_dir / video_id / "audio.mp3"
    assert expected_audio_path.is_file(), f"expected audio file at {expected_audio_path}"

    contents = expected_audio_path.read_bytes()
    assert contents == video_bytes, "expected audio file content to match video content"


def test_should_publish_audio_extracted_event(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
    video_id: str,
):
    consumer = RabbitMQVideoUploadedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    fake_channel.start_consuming.side_effect = KeyboardInterrupt

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    callback = fake_channel._consume_callback
    assert callback is not None, "basic_consume callback was not registered"

    fake_method = MagicMock()
    fake_method.delivery_tag = 42

    callback(fake_channel, fake_method, None, message_body)

    assert len(fake_publisher.published_events) == 1, f"expected one published event, got {len(fake_publisher.published_events)}"
    event = fake_publisher.published_events[0]
    assert event.video_id == video_id, f"expected video_id {video_id}, got {event.video_id}"


def test_should_acknowledge_message_after_processing(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_publisher: FakeAudioEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
):
    consumer = RabbitMQVideoUploadedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        publisher=fake_publisher,
    )

    # Start consuming, capture callback, then stop
    fake_channel.start_consuming.side_effect = KeyboardInterrupt

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    callback = fake_channel._consume_callback
    assert callback is not None, "basic_consume callback was not registered"

    fake_method = MagicMock()
    fake_method.delivery_tag = 42

    callback(fake_channel, fake_method, None, message_body)

    fake_channel.basic_ack.assert_called_once_with(delivery_tag=42), "expected basic_ack to be called once with delivery_tag=42"