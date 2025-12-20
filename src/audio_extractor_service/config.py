import os

from pydantic import BaseModel

from src.audio_extractor_service.rabbitmq_consumer import RabbitMQConsumerConfig
from src.shared.config import AudioExtractedRabbitMQConfig


class AudioExtractorConfig(BaseModel):
    """Configuration for the audio extractor service."""
    consumer: RabbitMQConsumerConfig
    publisher: AudioExtractedRabbitMQConfig


def load_config() -> AudioExtractorConfig:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASS", "guest")

    video_uploaded_queue = os.getenv("RABBITMQ_QUEUE", "video.uploaded")
    audio_extracted_queue = os.getenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")

    consumer_cfg = RabbitMQConsumerConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=video_uploaded_queue,
    )

    publisher_cfg = AudioExtractedRabbitMQConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=audio_extracted_queue,
    )

    return AudioExtractorConfig(
        consumer=consumer_cfg,
        publisher=publisher_cfg,
    )
