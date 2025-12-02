import json
from pathlib import Path

import pika
from pydantic import BaseModel

from src.upload_service.events import VideoUploadedEvent
from src.audio_extractor_service.worker import AudioEventPublisher, process_video_uploaded_event


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
        base_output_dir: Path,
        publisher: AudioEventPublisher,
    ) -> None:
        self._config = config
        self._base_output_dir = base_output_dir
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
                base_output_dir=self._base_output_dir,
                publisher=self._publisher,
            )

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(
            queue=self._config.queue_name,
            on_message_callback=_callback,
        )

        channel.start_consuming()