import os
from pydantic import BaseModel

from src.analysis_service.rabbitmq_consumer import RabbitMQConsumerConfig
from src.analysis_service.rabbitmq_publisher import RabbitMQConfig as PublisherConfig


class AnalysisServiceConfig(BaseModel):
    consumer: RabbitMQConsumerConfig
    publisher: PublisherConfig
    mongo_uri: str
    mongo_db_name: str


def load_config() -> AnalysisServiceConfig:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASS", "guest")

    transcript_created_queue = os.getenv("TRANSCRIPT_CREATED_QUEUE", "transcript.created")
    analysis_completed_queue = os.getenv("ANALYSIS_COMPLETED_QUEUE", "analysis.completed")

    mongo_uri = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
    mongo_db_name = os.getenv("MONGO_DB_NAME", "therapy_analysis")

    consumer_config = RabbitMQConsumerConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=transcript_created_queue,
    )

    publisher_config = PublisherConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=analysis_completed_queue,
    )

    return AnalysisServiceConfig(
        consumer=consumer_config,
        publisher=publisher_config,
        mongo_uri=mongo_uri,
        mongo_db_name=mongo_db_name,
    )
