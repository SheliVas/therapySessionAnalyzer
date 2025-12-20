import pika

from src.transcription_service.domain import TranscriptCreatedEvent, TranscriptEventPublisher
from src.shared.config import TranscriptCreatedPublisherConfig


class RabbitMQTranscriptEventPublisher(TranscriptEventPublisher):

    def __init__(self, config: TranscriptCreatedPublisherConfig) -> None:
        self._config = config

    def publish_transcript_created(self, event: TranscriptCreatedEvent) -> None:
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

            body = event.model_dump_json().encode("utf-8")

            channel.basic_publish(
                exchange="",
                routing_key=self._config.queue_name,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
        finally:
            connection.close()
