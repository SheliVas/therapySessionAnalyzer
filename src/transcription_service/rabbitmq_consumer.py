import json

import pika
from pydantic import BaseModel

from src.audio_extractor_service.domain import AudioExtractedEvent
from src.transcription_service.domain import TranscriptionBackend, StorageClient
from src.transcription_service.worker import TranscriptEventPublisher, process_audio_extracted_event


class RabbitMQConsumerConfig(BaseModel):
    host: str
    port: int
    username: str
    password: str
    queue_name: str = "audio.extracted"


class RabbitMQAudioExtractedConsumer:
    def __init__(
        self,
        config: RabbitMQConsumerConfig,
        storage_client: StorageClient,
        backend: TranscriptionBackend,
        publisher: TranscriptEventPublisher,
    ) -> None:
        self._config = config
        self._storage_client = storage_client
        self._backend = backend
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
            event = AudioExtractedEvent(**data)

            process_audio_extracted_event(
                event,
                storage_client=self._storage_client,
                backend=self._backend,
                publisher=self._publisher,
            )

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(
            queue=self._config.queue_name,
            on_message_callback=_callback,
        )

        channel.start_consuming()
