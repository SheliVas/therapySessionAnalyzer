import json

import pika

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.audio_extractor_service.worker import AudioEventPublisher
from src.shared.config import AudioExtractedPublisherConfig


class RabbitMQAudioEventPublisher(AudioEventPublisher):

    def __init__(self, config: AudioExtractedPublisherConfig) -> None:
        self._config = config

    def publish_audio_extracted(self, event: AudioExtractedEvent) -> None:
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
