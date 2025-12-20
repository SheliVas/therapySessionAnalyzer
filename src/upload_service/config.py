import os

from src.shared.config import MongoConfig, VideoUploadedPublisherConfig

# Re-export get_mongo_config from shared for backward compatibility
from src.shared.config import get_mongo_config, get_minio_config  # noqa: F401


def get_rabbitmq_config() -> VideoUploadedPublisherConfig:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASS", "guest")
    queue_name = os.getenv("RABBITMQ_QUEUE", "video.uploaded")

    return VideoUploadedPublisherConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=queue_name,
    )
