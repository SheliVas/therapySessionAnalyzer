import json
import logging

import pika

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import TranscriptionBackend, StorageClient, VideosRepository
from src.transcription_service.worker import TranscriptEventPublisher, process_audio_extracted_event
from src.shared.config import AudioExtractedConsumerConfig


RabbitMQConsumerConfig = AudioExtractedConsumerConfig

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class RabbitMQAudioExtractedConsumer:
    def __init__(
        self,
        config: RabbitMQConsumerConfig,
        storage_client: StorageClient,
        backend: TranscriptionBackend,
        repository: VideosRepository,
        publisher: TranscriptEventPublisher,
    ) -> None:
        self._config = config
        self._storage_client = storage_client
        self._backend = backend
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
        )

        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=self._config.queue_name, durable=True)

        def _callback(ch, method, properties, body: bytes) -> None:
            try:
                data = json.loads(body.decode("utf-8"))
                event = AudioExtractedEvent(**data)

                process_audio_extracted_event(
                    event,
                    storage_client=self._storage_client,
                    backend=self._backend,
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
