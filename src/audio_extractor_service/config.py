import os
from pathlib import Path

from pydantic import BaseModel

from src.audio_extractor_service.rabbitmq_consumer import RabbitMQConsumerConfig


class AudioExtractorConfig(BaseModel):
    rabbitmq: RabbitMQConsumerConfig
    base_output_dir: Path


def load_config() -> AudioExtractorConfig:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASS", "guest")
    queue_name = os.getenv("RABBITMQ_QUEUE", "video.uploaded")

    base_output_dir_str = os.getenv("AUDIO_OUTPUT_BASE_DIR", "/app/data/audio")
    base_output_dir = Path(base_output_dir_str)

    rabbitmq_cfg = RabbitMQConsumerConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=queue_name,
    )

    return AudioExtractorConfig(
        rabbitmq=rabbitmq_cfg,
        base_output_dir=base_output_dir,
    )
