import os
import time
from pathlib import Path

import pika.exceptions
from pymongo import MongoClient

from src.transcription_service.rabbitmq_consumer import (
    RabbitMQConsumerConfig,
    RabbitMQAudioExtractedConsumer,
)
from src.transcription_service.rabbitmq_publisher import RabbitMQTranscriptEventPublisher
from src.transcription_service.domain import TranscriptionBackend, StorageClient
from src.transcription_service.backend import AssemblyAITranscriptionBackend
from src.transcription_service.config import load_config
from src.shared.config import (
    get_minio_config,
    get_mongo_config,
)
from src.shared.minio_storage import MinioStorage
from src.shared.videos_repository import MongoVideosRepository


def create_production_app() -> dict:
    """
    Create production app with real dependencies wired together.
    
    Builds:
    - MinioStorage from shared config
    - MongoVideosRepository from MongoDB client
    - RabbitMQ consumer and publisher configs
    - RabbitMQAudioExtractedConsumer with all dependencies
    
    Returns:
        Dictionary with storage_client, repository, publisher, and consumer.
        
    Raises:
        KeyError: If required environment variables are missing.
    """
    config = load_config()

    storage_client = MinioStorage(get_minio_config())

    mongo_config = get_mongo_config()
    mongo_client = MongoClient(mongo_config.uri)
    repository = MongoVideosRepository(mongo_client, mongo_config.db_name)

    publisher = RabbitMQTranscriptEventPublisher(config.publisher)
    
    backend = AssemblyAITranscriptionBackend(
        api_key=config.assemblyai_api_key,
        base_url=config.assemblyai_base_url
    )
    
    consumer = RabbitMQAudioExtractedConsumer(
        config=config.consumer,
        storage_client=storage_client,
        backend=backend,
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
