import os
from pathlib import Path

from pydantic import BaseModel

from src.transcription_service.rabbitmq_consumer import RabbitMQConsumerConfig
from src.transcription_service.rabbitmq_publisher import RabbitMQConfig as PublisherConfig


class TranscriptionConfig(BaseModel):
    consumer: RabbitMQConsumerConfig
    publisher: PublisherConfig
    base_output_dir: Path


def load_config() -> TranscriptionConfig:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASS", "guest")

    audio_extracted_queue = os.getenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    transcript_created_queue = os.getenv("TRANSCRIPT_CREATED_QUEUE", "transcript.created")

    base_output_dir_str = os.getenv("TRANSCRIPT_OUTPUT_BASE_DIR", "/app/data/transcripts")
    base_output_dir = Path(base_output_dir_str)

    consumer_cfg = RabbitMQConsumerConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=audio_extracted_queue,
    )

    publisher_cfg = PublisherConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=transcript_created_queue,
    )

    return TranscriptionConfig(
        consumer=consumer_cfg,
        publisher=publisher_cfg,
        base_output_dir=base_output_dir,
    )
