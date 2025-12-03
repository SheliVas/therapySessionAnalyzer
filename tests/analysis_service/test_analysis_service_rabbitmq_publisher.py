import json

import pika
import pytest

from src.analysis_service.worker import AnalysisCompletedEvent
from src.analysis_service.rabbitmq_publisher import (
    RabbitMQConfig,
    RabbitMQAnalysisEventPublisher,
)


# --- Fixtures ---


@pytest.fixture
def config() -> RabbitMQConfig:
    return RabbitMQConfig(
        host="rabbitmq",
        port=5672,
        username="guest",
        password="guest",
        queue_name="analysis.completed",
    )


@pytest.fixture
def event() -> AnalysisCompletedEvent:
    return AnalysisCompletedEvent(
        video_id="video-123",
        word_count=42,
        extra={"sentiment": "positive"},
    )


# --- Unit Tests ---


@pytest.mark.unit
def test_should_connect_with_correct_parameters(
    config: RabbitMQConfig,
    event: AnalysisCompletedEvent,
    mocker,
    mock_connection,
) -> None:
    mock_pika = mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQAnalysisEventPublisher(config)
    publisher.publish_analysis_completed(event)

    mock_pika.assert_called_once()
    params = mock_pika.call_args[0][0]
    assert isinstance(params, pika.ConnectionParameters), (
        f"expected pika.ConnectionParameters, got {type(params)}"
    )
    assert params.host == config.host, f"expected host {config.host}, got {params.host}"
    assert params.port == config.port, f"expected port {config.port}, got {params.port}"
    assert params.credentials.username == config.username, (
        f"expected username {config.username}, got {params.credentials.username}"
    )
    assert params.credentials.password == config.password, (
        f"expected password {config.password}, got {params.credentials.password}"
    )


@pytest.mark.unit
def test_should_declare_queue_with_correct_name_and_durable(
    config: RabbitMQConfig,
    event: AnalysisCompletedEvent,
    mocker,
    mock_connection,
    mock_channel,
) -> None:
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQAnalysisEventPublisher(config)
    publisher.publish_analysis_completed(event)

    mock_channel.queue_declare.assert_called_once_with(
        queue=config.queue_name,
        durable=True,
    )


@pytest.mark.unit
def test_should_publish_event_as_json_to_correct_queue(
    config: RabbitMQConfig,
    event: AnalysisCompletedEvent,
    mocker,
    mock_connection,
    mock_channel,
) -> None:
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQAnalysisEventPublisher(config)
    publisher.publish_analysis_completed(event)

    mock_channel.basic_publish.assert_called_once()
    call_kwargs = mock_channel.basic_publish.call_args.kwargs

    assert call_kwargs.get("exchange") == "", (
        f"expected exchange to be '', got {call_kwargs.get('exchange')}"
    )
    assert call_kwargs.get("routing_key") == config.queue_name, (
        f"expected routing_key to be {config.queue_name}, got {call_kwargs.get('routing_key')}"
    )

    body_dict = json.loads(call_kwargs.get("body"))
    assert body_dict["video_id"] == event.video_id, (
        f"expected video_id {event.video_id}, got {body_dict['video_id']}"
    )
    assert body_dict["word_count"] == event.word_count, (
        f"expected word_count {event.word_count}, got {body_dict['word_count']}"
    )
    assert body_dict["extra"] == event.extra, (
        f"expected extra {event.extra}, got {body_dict['extra']}"
    )


@pytest.mark.unit
def test_should_close_connection_after_publishing(
    config: RabbitMQConfig,
    event: AnalysisCompletedEvent,
    mocker,
    mock_connection,
) -> None:
    mocker.patch("pika.BlockingConnection", return_value=mock_connection)

    publisher = RabbitMQAnalysisEventPublisher(config)
    publisher.publish_analysis_completed(event)

    mock_connection.close.assert_called_once()
