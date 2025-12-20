import os
import time

import pika.exceptions
from pymongo import MongoClient

from src.audio_extractor_service.config import RabbitMQConsumerConfig
from src.audio_extractor_service.rabbitmq_consumer import RabbitMQVideoUploadedConsumer
from src.audio_extractor_service.rabbitmq_publisher import RabbitMQAudioEventPublisher
from src.audio_extractor_service.ffmpeg_converter import FFmpegAudioConverter
from src.shared.config import MinIOConfig, AudioExtractedPublisherConfig
from src.shared.minio_storage import MinioStorage
from src.shared.videos_repository import MongoVideosRepository


def create_production_app() -> dict:
    """
    Create production app with all dependencies.
    
    Returns:
        Dictionary with storage_client, repository, publisher, and consumer.
        
    Raises:
        KeyError: If required environment variables are missing.
    """
    consumer_config = RabbitMQConsumerConfig(
        host=os.environ["RABBITMQ_HOST"],
        port=int(os.environ["RABBITMQ_PORT"]),
        username=os.environ["RABBITMQ_USER"],
        password=os.environ["RABBITMQ_PASS"],
        queue_name=os.environ.get("RABBITMQ_QUEUE", "video.uploaded"),
    )

    publisher_config = AudioExtractedPublisherConfig(
        host=os.environ["RABBITMQ_HOST"],
        port=int(os.environ["RABBITMQ_PORT"]),
        username=os.environ["RABBITMQ_USER"],
        password=os.environ["RABBITMQ_PASS"],
        queue_name=os.environ.get("AUDIO_EXTRACTED_QUEUE", "audio.extracted"),
    )

    minio_config = MinIOConfig(
        endpoint=os.environ["MINIO_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",
    )
    storage_client = MinioStorage(minio_config)

    mongo_uri = os.environ["MONGO_URI"]
    mongo_db = os.environ["MONGO_DB"]
    mongo_client = MongoClient(mongo_uri)
    repository = MongoVideosRepository(mongo_client, mongo_db)

    publisher = RabbitMQAudioEventPublisher(publisher_config)

    audio_converter = FFmpegAudioConverter()

    consumer = RabbitMQVideoUploadedConsumer(
        config=consumer_config,
        storage_client=storage_client,
        audio_converter=audio_converter,
        repository=repository,
        publisher=publisher,
    )

    return {
        "storage_client": storage_client,
        "repository": repository,
        "publisher": publisher,
        "consumer": consumer,
    }


def main() -> None:
    app = create_production_app()
    consumer = app["consumer"]

    max_retries = 10
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect to RabbitMQ (attempt {attempt + 1}/{max_retries})...")
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
