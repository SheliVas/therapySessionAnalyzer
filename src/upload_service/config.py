import os
from dataclasses import dataclass

from src.upload_service.rabbitmq_publisher import RabbitMQConfig


@dataclass
class MongoConfig:
    """Configuration for MongoDB connection."""
    uri: str
    db_name: str = "therapy_analysis"


@dataclass
class MinIOConfig:
    """Configuration for MinIO storage client."""
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str = "therapy-videos"
    secure: bool = False


def get_rabbitmq_config() -> RabbitMQConfig:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASS", "guest")
    queue_name = os.getenv("RABBITMQ_QUEUE", "video.uploaded")

    return RabbitMQConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=queue_name,
    )


def get_minio_config() -> MinIOConfig:
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    bucket = os.getenv("MINIO_BUCKET", "therapy-videos")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    return MinIOConfig(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket=bucket,
        secure=secure,
    )


def get_mongo_config() -> MongoConfig:
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "therapy_analysis")
    
    return MongoConfig(
        uri=uri,
        db_name=db_name,
    )
