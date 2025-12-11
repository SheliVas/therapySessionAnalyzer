
import json
import pika
import pytest

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.audio_extractor_service.rabbitmq_publisher import (
    RabbitMQConfig,
    RabbitMQAudioEventPublisher,
)


@pytest.fixture
def config() -> RabbitMQConfig:
    return RabbitMQConfig(
        host="rabbitmq",
        port=5672,
        username="guest",
        password="guest",
        queue_name="audio.extracted",
    )


@pytest.fixture
def event() -> AudioExtractedEvent:
    return AudioExtractedEvent(
        video_id="video-123",
        bucket="therapy-audio",
        key="audio/video-123/audio.mp3",
    )


def test_should_connect_with_correct_parameters(
    config: RabbitMQConfig,
    event: AudioExtractedEvent,
    mocker,
    mock_connection,
) -> None:
    mock_blocking_connection = mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQAudioEventPublisher(config)
    publisher.publish_audio_extracted(event)

    mock_blocking_connection.assert_called_once()
    call_args = mock_blocking_connection.call_args
    params = call_args[0][0]

    assert isinstance(params, pika.ConnectionParameters)
    assert params.host == config.host
    assert params.port == config.port
    assert params.credentials.username == config.username
    assert params.credentials.password == config.password


def test_should_declare_queue_with_correct_name_and_durable(
    config: RabbitMQConfig,
    event: AudioExtractedEvent,
    mocker,
    mock_connection,
    mock_channel,
) -> None:
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQAudioEventPublisher(config)
    publisher.publish_audio_extracted(event)

    mock_channel.queue_declare.assert_called_once_with(
        queue=config.queue_name,
        durable=True,
    )


def test_should_publish_event_as_json_to_correct_queue(
    config: RabbitMQConfig,
    event: AudioExtractedEvent,
    mocker,
    mock_connection,
    mock_channel,
) -> None:
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQAudioEventPublisher(config)
    publisher.publish_audio_extracted(event)

    mock_channel.basic_publish.assert_called_once()
    call_kwargs = mock_channel.basic_publish.call_args.kwargs

    assert call_kwargs.get("exchange") == ""
    assert call_kwargs.get("routing_key") == config.queue_name

    body_dict = json.loads(call_kwargs.get("body"))
    assert body_dict["video_id"] == event.video_id
    assert body_dict["bucket"] == event.bucket
    assert body_dict["key"] == event.key


def test_should_close_connection_after_publishing(
    config: RabbitMQConfig,
    event: AudioExtractedEvent,
    mocker,
    mock_connection,
) -> None:
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQAudioEventPublisher(config)
    publisher.publish_audio_extracted(event)

    mock_connection.close.assert_called_once()
