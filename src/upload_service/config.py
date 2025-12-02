import os

from src.upload_service.rabbitmq_publisher import RabbitMQConfig


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
