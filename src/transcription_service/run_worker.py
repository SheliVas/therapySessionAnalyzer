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
from src.transcription_service.domain import TranscriptionBackend, StorageClient


class StubTranscriptionBackend(TranscriptionBackend):
    """Stub backend that returns a placeholder transcript."""

    def transcribe(self, audio_bytes: bytes) -> str:
        return f"[Stub transcript for {len(audio_bytes)} bytes]"


class StubStorageClient:
    """Stub storage client."""
    def download_file(self, bucket: str, key: str) -> bytes:
        return b"stub-audio-content"
    
    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        print(f"Uploaded {len(content)} bytes to {bucket}/{key}")


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

    publisher = RabbitMQTranscriptEventPublisher(publisher_config)
    backend = StubTranscriptionBackend()
    storage_client = StubStorageClient()

    consumer = RabbitMQAudioExtractedConsumer(
        config=consumer_config,
        storage_client=storage_client,
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
