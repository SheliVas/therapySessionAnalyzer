import json

import pika

from src.upload_service.domain import VideoUploadedEvent, VideoEventPublisher
from src.shared.config import VideoUploadedPublisherConfig


class RabbitMQVideoEventPublisher(VideoEventPublisher):
    def __init__(self, config: VideoUploadedPublisherConfig) -> None:
        self._config = config

    def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
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
            )
        finally:
            connection.close()