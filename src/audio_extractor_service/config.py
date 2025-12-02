import os
from pathlib import Path

from pydantic import BaseModel

from src.audio_extractor_service.rabbitmq_consumer import RabbitMQConsumerConfig
from src.audio_extractor_service.rabbitmq_publisher import RabbitMQConfig as RabbitMQPublisherConfig


class AudioExtractorConfig(BaseModel):
    consumer: RabbitMQConsumerConfig
    publisher: RabbitMQPublisherConfig
    base_output_dir: Path


def load_config() -> AudioExtractorConfig:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASS", "guest")

    video_uploaded_queue = os.getenv("RABBITMQ_QUEUE", "video.uploaded")
    audio_extracted_queue = os.getenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")

    base_output_dir_str = os.getenv("AUDIO_OUTPUT_BASE_DIR", "/app/data/audio")
    base_output_dir = Path(base_output_dir_str)

    consumer_cfg = RabbitMQConsumerConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=video_uploaded_queue,
    )

    publisher_cfg = RabbitMQPublisherConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=audio_extracted_queue,
    )

    return AudioExtractorConfig(
        consumer=consumer_cfg,
        publisher=publisher_cfg,
        base_output_dir=base_output_dir,
    )
