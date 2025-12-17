import os

from src.shared.config import MinIOConfig, get_minio_config, MongoConfig, get_mongo_config, VideoUploadedPublisherConfig


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


def get_mongo_config() -> MongoConfig:
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "therapy_analysis")
    
    return MongoConfig(
        uri=uri,
        db_name=db_name,
    )
