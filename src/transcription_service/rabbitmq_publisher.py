import json

import pika
from pydantic import BaseModel

from src.transcription_service.domain import TranscriptCreatedEvent
from src.transcription_service.worker import TranscriptEventPublisher


class RabbitMQConfig(BaseModel):
    """Configuration for RabbitMQ connection."""

    host: str
    port: int
    username: str
    password: str
    queue_name: str = "transcript.created"


class RabbitMQTranscriptEventPublisher(TranscriptEventPublisher):
    """RabbitMQ-backed publisher for TranscriptCreatedEvent."""

    def __init__(self, config: RabbitMQConfig) -> None:
        self._config = config

    def publish_transcript_created(self, event: TranscriptCreatedEvent) -> None:
        """Publish a TranscriptCreatedEvent to RabbitMQ."""
        credentials = pika.PlainCredentials(
            self._config.username,
            self._config.password,
        )
        parameters = pika.ConnectionParameters(
            host=self._config.host,
            port=self._config.port,
            credentials=credentials,
        )

        connection = pika.BlockingConnection(parameters)
        try:
            channel = connection.channel()

            channel.queue_declare(queue=self._config.queue_name, durable=True)

            body = json.dumps(event.model_dump()).encode("utf-8")

            channel.basic_publish(
                exchange="",
                routing_key=self._config.queue_name,
                body=body,
            )
        finally:
            connection.close()
