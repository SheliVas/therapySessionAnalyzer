import os

from src.upload_service.rabbitmq_publisher import RabbitMQConfig


class MinIOConfig:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str = "therapy-videos",
    ):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket


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

    return MinIOConfig(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket=bucket,
    )
