import json
from pathlib import Path
from unittest.mock import MagicMock

import pika
import pytest

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import (
    TranscriptCreatedEvent,
    TranscriptionBackend,
)
from src.transcription_service.worker import TranscriptEventPublisher
from src.transcription_service.rabbitmq_consumer import (
    RabbitMQConsumerConfig,
    RabbitMQAudioExtractedConsumer,
)


class FakeTranscriptionBackend(TranscriptionBackend):

    def __init__(self, transcript_text: str) -> None:
        self.transcript_text = transcript_text
        self.calls: list[Path] = []

    def transcribe(self, audio_path: Path) -> str:
        self.calls.append(audio_path)
        return self.transcript_text


class FakeTranscriptEventPublisher(TranscriptEventPublisher):

    def __init__(self) -> None:
        self.published_events: list[TranscriptCreatedEvent] = []

    def publish_transcript_created(self, event: TranscriptCreatedEvent) -> None:
        self.published_events.append(event)


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
def base_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "data" / "transcripts"


@pytest.fixture
def message_body(video_id: str, audio_path: Path) -> bytes:
    return json.dumps({
        "video_id": video_id,
        "audio_path": str(audio_path),
    }).encode("utf-8")


@pytest.fixture
def fake_backend() -> FakeTranscriptionBackend:
    return FakeTranscriptionBackend(transcript_text="hello transcript")


@pytest.fixture
def fake_publisher() -> FakeTranscriptEventPublisher:
    return FakeTranscriptEventPublisher()


@pytest.fixture
def fake_channel() -> MagicMock:
    channel = MagicMock()
    channel._consume_callback = None

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


def test_should_connect_with_correct_parameters(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
) -> None:
    consumer = RabbitMQAudioExtractedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        backend=fake_backend,
        publisher=fake_publisher,
    )

    fake_channel.start_consuming.side_effect = KeyboardInterrupt

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    assert len(mock_pika) == 1, f"expected 1 connection attempt, got {len(mock_pika)}"
    params = mock_pika[0]
    assert params.host == config.host, f"expected host {config.host}, got {params.host}"
    assert params.port == config.port, f"expected port {config.port}, got {params.port}"
    assert params.credentials.username == config.username, (
        f"expected username {config.username}, got {params.credentials.username}"
    )
    assert params.credentials.password == config.password, (
        f"expected password {config.password}, got {params.credentials.password}"
    )


def test_should_declare_queue_durable(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
) -> None:
    consumer = RabbitMQAudioExtractedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        backend=fake_backend,
        publisher=fake_publisher,
    )

    fake_channel.start_consuming.side_effect = KeyboardInterrupt

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    fake_channel.queue_declare.assert_called_once_with(
        queue=config.queue_name,
        durable=True,
    )


def test_should_process_message_and_create_transcript_file(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
    video_id: str,
) -> None:
    consumer = RabbitMQAudioExtractedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        backend=fake_backend,
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

    expected_transcript_path = base_output_dir / video_id / "transcript.txt"
    assert expected_transcript_path.is_file(), (
        f"expected transcript file at {expected_transcript_path}, but it does not exist"
    )

    contents = expected_transcript_path.read_text()
    assert contents == fake_backend.transcript_text, (
        f"expected transcript content '{fake_backend.transcript_text}', got '{contents}'"
    )


def test_should_call_backend_with_correct_audio_path(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
    audio_path: Path,
) -> None:
    consumer = RabbitMQAudioExtractedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        backend=fake_backend,
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

    assert len(fake_backend.calls) == 1, f"expected 1 call to backend, got {len(fake_backend.calls)}"
    assert fake_backend.calls[0] == audio_path, (
        f"expected audio_path {audio_path}, got {fake_backend.calls[0]}"
    )


def test_should_publish_transcript_created_event(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
    video_id: str,
) -> None:
    consumer = RabbitMQAudioExtractedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        backend=fake_backend,
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

    assert len(fake_publisher.published_events) == 1, (
        f"expected 1 published event, got {len(fake_publisher.published_events)}"
    )
    event = fake_publisher.published_events[0]
    assert event.video_id == video_id, f"expected video_id {video_id}, got {event.video_id}"


def test_should_acknowledge_message_after_processing(
    config: RabbitMQConsumerConfig,
    base_output_dir: Path,
    fake_backend: FakeTranscriptionBackend,
    fake_publisher: FakeTranscriptEventPublisher,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
) -> None:
    consumer = RabbitMQAudioExtractedConsumer(
        config=config,
        base_output_dir=base_output_dir,
        backend=fake_backend,
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

    fake_channel.basic_ack.assert_called_once_with(delivery_tag=42)
