import json

import pika
from pydantic import BaseModel

from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import (
    AudioEventPublisher,
    StorageClient,
    AudioConverter,
)
from src.audio_extractor_service.worker import process_video_uploaded_event


class RabbitMQConsumerConfig(BaseModel):
    host: str
    port: int
    username: str
    password: str
    queue_name: str = "video.uploaded"


class RabbitMQVideoUploadedConsumer:
    def __init__(
        self,
        config: RabbitMQConsumerConfig,
        storage_client: StorageClient,
        audio_converter: AudioConverter,
        publisher: AudioEventPublisher,
    ) -> None:
        self._config = config
        self._storage_client = storage_client
        self._audio_converter = audio_converter
        self._publisher = publisher

    def run_forever(self) -> None:
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
        channel = connection.channel()
        channel.queue_declare(queue=self._config.queue_name, durable=True)

        def _callback(ch, method, properties, body: bytes) -> None:
            data = json.loads(body.decode("utf-8"))
            event = VideoUploadedEvent(**data)

            process_video_uploaded_event(
                event,
                storage_client=self._storage_client,
                audio_converter=self._audio_converter,
                publisher=self._publisher,
            )

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(
            queue=self._config.queue_name,
            on_message_callback=_callback,
        )

        channel.start_consuming()