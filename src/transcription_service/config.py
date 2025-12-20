import os

from pydantic import BaseModel

from src.transcription_service.rabbitmq_consumer import RabbitMQConsumerConfig
from src.shared.config import TranscriptCreatedRabbitMQConfig


class TranscriptionConfig(BaseModel):
    """Configuration for the transcription service."""
    consumer: RabbitMQConsumerConfig
    publisher: TranscriptCreatedRabbitMQConfig
    assemblyai_api_key: str
    assemblyai_base_url: str = "https://api.assemblyai.com"


def load_config() -> TranscriptionConfig:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASS", "guest")

    audio_extracted_queue = os.getenv("AUDIO_EXTRACTED_QUEUE", "audio.extracted")
    transcript_created_queue = os.getenv("TRANSCRIPT_CREATED_QUEUE", "transcript.created")

    assemblyai_api_key = os.environ["ASSEMBLYAI_API_KEY"]
    assemblyai_base_url = os.getenv("ASSEMBLYAI_BASE_URL", "https://api.assemblyai.com")

    consumer_cfg = RabbitMQConsumerConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=audio_extracted_queue,
    )

    publisher_cfg = TranscriptCreatedRabbitMQConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=transcript_created_queue,
    )

    return TranscriptionConfig(
        consumer=consumer_cfg,
        publisher=publisher_cfg,
        assemblyai_api_key=assemblyai_api_key,
        assemblyai_base_url=assemblyai_base_url,
    )
