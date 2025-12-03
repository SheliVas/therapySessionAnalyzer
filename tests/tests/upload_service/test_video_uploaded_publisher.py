import json
from unittest.mock import MagicMock

import pika
import pytest

from src.upload_service.domain import VideoUploadedEvent
from src.upload_service.rabbitmq_publisher import (
    RabbitMQConfig,
    RabbitMQVideoEventPublisher,
)


@pytest.fixture
def config() -> RabbitMQConfig:
    return RabbitMQConfig(
        host="rabbitmq",
        port=5672,
        username="guest",
        password="guest",
        queue_name="video.uploaded",
    )


@pytest.fixture
def event() -> VideoUploadedEvent:
    return VideoUploadedEvent(
        video_id="video-123",
        filename="session1.mp4",
        storage_path="data/uploads/video-123/session1.mp4",
    )


@pytest.fixture
def fake_channel() -> MagicMock:
    return MagicMock()


@pytest.fixture
def fake_connection(fake_channel: MagicMock) -> MagicMock:
    conn = MagicMock()
    conn.channel.return_value = fake_channel
    return conn


@pytest.fixture
def mock_pika(monkeypatch, fake_connection: MagicMock) -> list[pika.ConnectionParameters]:
    captured_params: list[pika.ConnectionParameters] = []

    def fake_blocking_connection(params: pika.ConnectionParameters):
        captured_params.append(params)
        return fake_connection

    monkeypatch.setattr(pika, "BlockingConnection", fake_blocking_connection)
    return captured_params


def test_should_connect_with_correct_parameters(
    config: RabbitMQConfig,
    event: VideoUploadedEvent,
    mock_pika: list[pika.ConnectionParameters],
):
    publisher = RabbitMQVideoEventPublisher(config)
    publisher.publish_video_uploaded(event)

    assert len(mock_pika) == 1, f"expected 1 connection attempt, got {len(mock_pika)}"
    params = mock_pika[0]
    assert isinstance(params, pika.ConnectionParameters), f"expected pika.ConnectionParameters, got {type(params)}"
    assert params.host == config.host, f"expected host {config.host}, got {params.host}"
    assert params.port == config.port, f"expected port {config.port}, got {params.port}"
    assert params.credentials.username == config.username, f"expected username {config.username}, got {params.credentials.username}"
    assert params.credentials.password == config.password, f"expected password {config.password}, got {params.credentials.password}"


def test_should_declare_queue_with_correct_name_and_durable(
    config: RabbitMQConfig,
    event: VideoUploadedEvent,
    mock_pika: list,
    fake_channel: MagicMock,
):
    publisher = RabbitMQVideoEventPublisher(config)
    publisher.publish_video_uploaded(event)

    fake_channel.queue_declare.assert_called_once_with(
        queue=config.queue_name,
        durable=True,
    ), f"expected queue_declare called with queue={config.queue_name} and durable=True"


def test_should_publish_event_as_json_to_correct_queue(
    config: RabbitMQConfig,
    event: VideoUploadedEvent,
    mock_pika: list,
    fake_channel: MagicMock,
):
    publisher = RabbitMQVideoEventPublisher(config)
    publisher.publish_video_uploaded(event)

    fake_channel.basic_publish.assert_called_once(), f"expected basic_publish to be called once, got {fake_channel.basic_publish.call_count}"
    call_kwargs = fake_channel.basic_publish.call_args.kwargs

    assert call_kwargs.get("exchange") == "", f"expected exchange to be '', got {call_kwargs.get('exchange')}"
    assert call_kwargs.get("routing_key") == config.queue_name, f"expected routing_key to be {config.queue_name}, got {call_kwargs.get('routing_key')}"

    body_dict = json.loads(call_kwargs.get("body"))
    assert body_dict["video_id"] == event.video_id, f"expected video_id {event.video_id}, got {body_dict['video_id']}"
    assert body_dict["filename"] == event.filename, f"expected filename {event.filename}, got {body_dict['filename']}"
    assert body_dict["storage_path"] == event.storage_path, f"expected storage_path {event.storage_path}, got {body_dict['storage_path']}"


def test_should_close_connection_after_publishing(
    config: RabbitMQConfig,
    event: VideoUploadedEvent,
    mock_pika: list,
    fake_connection: MagicMock,
):
    publisher = RabbitMQVideoEventPublisher(config)
    publisher.publish_video_uploaded(event)

    fake_connection.close.assert_called_once(), f"expected close to be called once, got {fake_connection.close.call_count}"