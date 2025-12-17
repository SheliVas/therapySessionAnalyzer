import os
from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class MinIOConfig:
    """Configuration for MinIO storage client."""
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str = "therapy-videos"
    secure: bool = False


@dataclass
class MongoConfig:
    """Configuration for MongoDB connection."""
    uri: str
    db_name: str = "therapy_analysis"


class RabbitMQConnectionConfig(BaseModel):
    """Base RabbitMQ connection configuration (used by both publishers and consumers)."""
    host: str
    port: int
    username: str
    password: str


# Queue-specific base configs with default queue names
class VideoUploadedQueueConfig(RabbitMQConnectionConfig):
    """Configuration for video.uploaded queue (connection + queue name)."""
    queue_name: str = "video.uploaded"


class AudioExtractedQueueConfig(RabbitMQConnectionConfig):
    """Configuration for audio.extracted queue (connection + queue name)."""
    queue_name: str = "audio.extracted"


class TranscriptCreatedQueueConfig(RabbitMQConnectionConfig):
    """Configuration for transcript.created queue (connection + queue name)."""
    queue_name: str = "transcript.created"


class AnalysisCompletedQueueConfig(RabbitMQConnectionConfig):
    """Configuration for analysis.completed queue (connection + queue name)."""
    queue_name: str = "analysis.completed"


# Publisher configs - extend queue configs
class VideoUploadedPublisherConfig(VideoUploadedQueueConfig):
    """Publisher config for video.uploaded queue."""
    pass


class AudioExtractedPublisherConfig(AudioExtractedQueueConfig):
    """Publisher config for audio.extracted queue."""
    pass


class TranscriptCreatedPublisherConfig(TranscriptCreatedQueueConfig):
    """Publisher config for transcript.created queue."""
    pass


class AnalysisCompletedPublisherConfig(AnalysisCompletedQueueConfig):
    """Publisher config for analysis.completed queue."""
    pass


# Consumer configs - extend queue configs (need queue_name for declaring/consuming)
class VideoUploadedConsumerConfig(VideoUploadedQueueConfig):
    """Consumer config for video.uploaded queue."""
    pass


class AudioExtractedConsumerConfig(AudioExtractedQueueConfig):
    """Consumer config for audio.extracted queue."""
    pass


class TranscriptCreatedConsumerConfig(TranscriptCreatedQueueConfig):
    """Consumer config for transcript.created queue."""
    pass


# Backward compatibility aliases
VideoUploadedRabbitMQConfig = VideoUploadedPublisherConfig
AudioExtractedRabbitMQConfig = AudioExtractedPublisherConfig
TranscriptCreatedRabbitMQConfig = TranscriptCreatedPublisherConfig
AnalysisCompletedRabbitMQConfig = AnalysisCompletedPublisherConfig


def get_minio_config() -> MinIOConfig:
    """Load MinIO configuration from environment variables."""
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
    """Load MongoDB configuration from environment variables."""
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "therapy_analysis")

    return MongoConfig(
        uri=uri,
        db_name=db_name,
    )
