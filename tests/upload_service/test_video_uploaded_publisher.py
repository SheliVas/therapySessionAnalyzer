import json
from datetime import datetime

import pika
import pytest

from src.upload_service.domain import VideoUploadedEvent
from src.upload_service.rabbitmq_publisher import (
    RabbitMQConfig,
    RabbitMQVideoEventPublisher,
)


# --- Fixtures ---


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
        bucket="therapy-videos",
        key="videos/video-123/session1.mp4",
        uploaded_at=datetime(2025, 12, 12, 12, 0, 0),
    )


# --- Unit Tests ---


@pytest.mark.unit
def test_should_connect_with_correct_parameters(
    config: RabbitMQConfig,
    event: VideoUploadedEvent,
    mocker,
    mock_connection,
):
    mock_pika = mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQVideoEventPublisher(config)
    publisher.publish_video_uploaded(event)

    mock_pika.assert_called_once()
    params = mock_pika.call_args[0][0]
    assert isinstance(params, pika.ConnectionParameters)
    assert params.host == config.host
    assert params.port == config.port
    assert params.credentials.username == config.username
    assert params.credentials.password == config.password


@pytest.mark.unit
def test_should_declare_queue_with_correct_name_and_durable(
    config: RabbitMQConfig,
    event: VideoUploadedEvent,
    mocker,
    mock_connection,
    mock_channel,
):
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQVideoEventPublisher(config)
    publisher.publish_video_uploaded(event)

    mock_channel.queue_declare.assert_called_once_with(
        queue=config.queue_name,
        durable=True,
    )


@pytest.mark.unit
def test_should_publish_event_as_json_to_correct_queue(
    config: RabbitMQConfig,
    event: VideoUploadedEvent,
    mocker,
    mock_connection,
    mock_channel,
):
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQVideoEventPublisher(config)
    publisher.publish_video_uploaded(event)

    mock_channel.basic_publish.assert_called_once()
    call_kwargs = mock_channel.basic_publish.call_args.kwargs

    assert call_kwargs.get("exchange") == ""
    assert call_kwargs.get("routing_key") == config.queue_name

    body_dict = json.loads(call_kwargs.get("body"))
    assert body_dict["video_id"] == event.video_id
    assert body_dict["filename"] == event.filename
    assert body_dict["bucket"] == event.bucket
    assert body_dict["key"] == event.key
    assert "uploaded_at" in body_dict


@pytest.mark.unit
def test_should_close_connection_after_publishing(
    config: RabbitMQConfig,
    event: VideoUploadedEvent,
    mocker,
    mock_connection,
):
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQVideoEventPublisher(config)
    publisher.publish_video_uploaded(event)

    mock_connection.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("video_id,filename,bucket,key", [
    ("", "test.mp4", "bucket", "key"),
    ("vid-1", "", "bucket", "key"),
    ("vid-1", "test.mp4", "", "key"),
    ("vid-1", "test.mp4", "bucket", ""),
])
def test_should_publish_event_with_empty_fields(
    config: RabbitMQConfig,
    mocker,
    mock_connection,
    mock_channel,
    video_id: str,
    filename: str,
    bucket: str,
    key: str,
):
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)
    event = VideoUploadedEvent(
        video_id=video_id,
        filename=filename,
        bucket=bucket,
        key=key,
        uploaded_at=datetime.now(),
    )

    publisher = RabbitMQVideoEventPublisher(config)
    publisher.publish_video_uploaded(event)

    mock_channel.basic_publish.assert_called_once()