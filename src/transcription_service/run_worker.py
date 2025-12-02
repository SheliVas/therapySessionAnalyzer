import os
import time
from pathlib import Path

import pika.exceptions

from src.transcription_service.rabbitmq_consumer import (
    RabbitMQConsumerConfig,
    RabbitMQAudioExtractedConsumer,
)
from src.transcription_service.rabbitmq_publisher import (
    RabbitMQConfig as PublisherConfig,
    RabbitMQTranscriptEventPublisher,
)
from src.transcription_service.domain import TranscriptionBackend


class StubTranscriptionBackend(TranscriptionBackend):
    """Stub backend that returns a placeholder transcript."""

    def transcribe(self, audio_path: Path) -> str:
        return f"[Stub transcript for {audio_path.name}]"


def main() -> None:
    consumer_config = RabbitMQConsumerConfig(
        host=os.environ["RABBITMQ_HOST"],
        port=int(os.environ["RABBITMQ_PORT"]),
        username=os.environ["RABBITMQ_USER"],
        password=os.environ["RABBITMQ_PASS"],
        queue_name=os.environ.get("AUDIO_EXTRACTED_QUEUE", "audio.extracted"),
    )

    publisher_config = PublisherConfig(
        host=os.environ["RABBITMQ_HOST"],
        port=int(os.environ["RABBITMQ_PORT"]),
        username=os.environ["RABBITMQ_USER"],
        password=os.environ["RABBITMQ_PASS"],
        queue_name=os.environ.get("TRANSCRIPT_CREATED_QUEUE", "transcript.created"),
    )

    base_output_dir = Path(
        os.environ.get("TRANSCRIPT_OUTPUT_BASE_DIR", "/app/data/transcripts")
    )
    publisher = RabbitMQTranscriptEventPublisher(publisher_config)
    backend = StubTranscriptionBackend()

    consumer = RabbitMQAudioExtractedConsumer(
        config=consumer_config,
        base_output_dir=base_output_dir,
        backend=backend,
        publisher=publisher,
    )

    max_retries = 10
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            print(
                f"Attempting to connect to RabbitMQ (attempt {attempt + 1}/{max_retries})..."
            )
            consumer.run_forever()
            break
        except pika.exceptions.AMQPConnectionError:
            if attempt < max_retries - 1:
                print(f"RabbitMQ not ready, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)  # exponential backoff, max 30s
            else:
                print("Failed to connect to RabbitMQ after maximum retries")
                raise


if __name__ == "__main__":
    main()
