import json
import time

import pika

from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import AnalysisBackend, StorageClient
from src.analysis_service.worker import (
    AnalysisEventPublisher,
    AnalysisRepository,
    process_transcript_created_event,
)
from src.shared.config import TranscriptCreatedConsumerConfig


RabbitMQConsumerConfig = TranscriptCreatedConsumerConfig


class RabbitMQTranscriptCreatedConsumer:

    def __init__(
        self,
        config: RabbitMQConsumerConfig,
        backend: AnalysisBackend,
        publisher: AnalysisEventPublisher,
        repository: AnalysisRepository,
        storage_client: StorageClient,
        videos_repository,
    ) -> None:
        """Initialize the consumer.

        Args:
            config: RabbitMQ configuration.
            backend: Analysis backend to use.
            publisher: Event publisher to use.
            repository: Repository to save analysis results.
            storage_client: Storage client to download transcripts.
            videos_repository: Videos repository to mark analysis status.
        """
        self._config = config
        self._backend = backend
        self._publisher = publisher
        self._repository = repository
        self._storage_client = storage_client
        self._videos_repository = videos_repository

    def run_forever(self) -> None:
        """Start consuming messages from the queue.

        Connects to RabbitMQ, declares the queue, and starts consuming messages.
        Each message is parsed as a TranscriptCreatedEvent and processed.
        """
        credentials = pika.PlainCredentials(
            self._config.username,
            self._config.password,
        )
        parameters = pika.ConnectionParameters(
            host=self._config.host,
            port=self._config.port,
            credentials=credentials,
        )

        while True:
            try:
                connection = pika.BlockingConnection(parameters)
                break
            except pika.exceptions.AMQPConnectionError:
                print("RabbitMQ not ready yet, retrying in 5 seconds...")
                time.sleep(5)
        channel = connection.channel()
        channel.queue_declare(queue=self._config.queue_name, durable=True)

        def _callback(ch, method, properties, body: bytes) -> None:
            data = json.loads(body.decode("utf-8"))
            event = TranscriptCreatedEvent(**data)

            process_transcript_created_event(
                event,
                backend=self._backend,
                publisher=self._publisher,
                repository=self._repository,
                storage_client=self._storage_client,
                videos_repository=self._videos_repository,
            )

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(
            queue=self._config.queue_name,
            on_message_callback=_callback,
        )

        channel.start_consuming()
