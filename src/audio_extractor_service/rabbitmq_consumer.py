import json
import logging

import pika

from src.shared.protocols import StorageClient, VideosRepository
from src.upload_service.domain import VideoUploadedEvent
from src.audio_extractor_service.domain import (
    AudioEventPublisher,
    AudioConverter,
)
from src.audio_extractor_service.worker import process_video_uploaded_event
from src.shared.config import VideoUploadedConsumerConfig


RabbitMQConsumerConfig = VideoUploadedConsumerConfig

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class RabbitMQVideoUploadedConsumer:
    def __init__(
        self,
        config: RabbitMQConsumerConfig,
        storage_client: StorageClient,
        audio_converter: AudioConverter,
        repository: VideosRepository,
        publisher: AudioEventPublisher,
    ) -> None:
        self._config = config
        self._storage_client = storage_client
        self._audio_converter = audio_converter
        self._repository = repository
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
            heartbeat=0,
        )

        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=self._config.queue_name, durable=True)
        channel.basic_qos(prefetch_count=1)

        def _callback(ch, method, properties, body: bytes) -> None:
            try:
                data = json.loads(body.decode("utf-8"))
                event = VideoUploadedEvent(**data)

                process_video_uploaded_event(
                    event,
                    storage_client=self._storage_client,
                    audio_converter=self._audio_converter,
                    repository=self._repository,
                    publisher=self._publisher,
                )

                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.exception(f"Error processing message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(
            queue=self._config.queue_name,
            on_message_callback=_callback,
        )

        channel.start_consuming()