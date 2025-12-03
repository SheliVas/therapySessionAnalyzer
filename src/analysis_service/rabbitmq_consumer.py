import json
import time

import pika
from pydantic import BaseModel

from src.transcription_service.domain import TranscriptCreatedEvent
from src.analysis_service.domain import AnalysisBackend
from src.analysis_service.worker import (
    AnalysisEventPublisher,
    AnalysisRepository,
    process_transcript_created_event,
)


class RabbitMQConsumerConfig(BaseModel):

    host: str
    port: int
    username: str
    password: str
    queue_name: str = "transcript.created"


class RabbitMQTranscriptCreatedConsumer:

    def __init__(
        self,
        config: RabbitMQConsumerConfig,
        backend: AnalysisBackend,
        publisher: AnalysisEventPublisher,
        repository: AnalysisRepository,
    ) -> None:
        """Initialize the consumer.

        Args:
            config: RabbitMQ configuration.
            backend: Analysis backend to use.
            publisher: Event publisher to use.
            repository: Repository to save analysis results.
        """
        self._config = config
        self._backend = backend
        self._publisher = publisher
        self._repository = repository

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
            )

            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(
            queue=self._config.queue_name,
            on_message_callback=_callback,
        )

        channel.start_consuming()
