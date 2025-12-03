import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pika

from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import AnalysisBackend, AnalysisResult
from src.analysis_service.worker import (
    AnalysisCompletedEvent,
    AnalysisEventPublisher,
    AnalysisRepository,
)
from src.analysis_service.rabbitmq_consumer import (
    RabbitMQConsumerConfig,
    RabbitMQTranscriptCreatedConsumer,
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
def video_id() -> str:
    return "video-123"


@pytest.fixture
def transcript_text() -> str:
    return "hello world hello"


@pytest.fixture
def transcript_path(tmp_path: Path, transcript_text: str) -> str:
    transcript_file = tmp_path / "transcript.txt"
    transcript_file.write_text(transcript_text)
    return str(transcript_file)


@pytest.fixture
def message_body(video_id: str, transcript_path: str) -> bytes:
    return json.dumps({
        "video_id": video_id,
        "transcript_path": transcript_path,
    }).encode("utf-8")


class FakeAnalysisBackend(AnalysisBackend):
    def __init__(self, video_id: str) -> None:
        self.video_id = video_id
        self.calls: list[str] = []

    def analyze(self, transcript_text: str) -> AnalysisResult:
        self.calls.append(transcript_text)
        word_count = len(transcript_text.split())
        return AnalysisResult(
            video_id=self.video_id,
            word_count=word_count,
            extra={"backend": "fake"},
        )


class FakeAnalysisEventPublisher(AnalysisEventPublisher):
    def __init__(self) -> None:
        self.published_events: list[AnalysisCompletedEvent] = []

    def publish_analysis_completed(self, event: AnalysisCompletedEvent) -> None:
        self.published_events.append(event)


class FakeAnalysisRepository(AnalysisRepository):
    def __init__(self) -> None:
        self.saved_events: list[AnalysisCompletedEvent] = []

    def save_analysis(self, event: AnalysisCompletedEvent) -> None:
        self.saved_events.append(event)


@pytest.fixture
def fake_backend(video_id: str) -> FakeAnalysisBackend:
    return FakeAnalysisBackend(video_id=video_id)


@pytest.fixture
def fake_publisher() -> FakeAnalysisEventPublisher:
    return FakeAnalysisEventPublisher()


@pytest.fixture
def fake_repository() -> FakeAnalysisRepository:
    return FakeAnalysisRepository()


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


# --- Tests ---


def test_should_connect_with_correct_parameters(
    config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
):
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
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
    assert params.credentials.username == config.username, f"expected username {config.username}, got {params.credentials.username}"
    assert params.credentials.password == config.password, f"expected password {config.password}, got {params.credentials.password}"


def test_should_declare_queue_durable(
    config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
):
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
    )

    fake_channel.start_consuming.side_effect = KeyboardInterrupt

    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        pass

    fake_channel.queue_declare.assert_called_once_with(
        queue=config.queue_name,
        durable=True,
    ), f"expected queue_declare called with queue={config.queue_name} and durable=True"


def test_should_process_message_and_call_backend(
    config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
    transcript_text: str,
):
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
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

    assert len(fake_backend.calls) == 1, f"expected backend to be called once, got {len(fake_backend.calls)}"
    assert fake_backend.calls[0] == transcript_text, f"expected transcript text '{transcript_text}', got '{fake_backend.calls[0]}'"


def test_should_save_exactly_one_event_after_processing(
    config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
    video_id: str,
):
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
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

    assert len(fake_repository.saved_events) == 1, f"expected one saved event, got {len(fake_repository.saved_events)}"
    event = fake_repository.saved_events[0]
    assert event.video_id == video_id, f"expected video_id {video_id}, got {event.video_id}"
    assert event.word_count == 3, f"expected word_count 3, got {event.word_count}"


def test_should_publish_exactly_one_event_after_processing(
    config: RabbitMQConsumerConfig,
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
    video_id: str,
):
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
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
    fake_backend: FakeAnalysisBackend,
    fake_publisher: FakeAnalysisEventPublisher,
    fake_repository: FakeAnalysisRepository,
    fake_channel: MagicMock,
    mock_pika: list[pika.ConnectionParameters],
    message_body: bytes,
):
    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config,
        backend=fake_backend,
        publisher=fake_publisher,
        repository=fake_repository,
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

    fake_channel.basic_ack.assert_called_once_with(delivery_tag=42), "expected basic_ack to be called once with delivery_tag=42"
