import os
from typing import Optional
from pydantic import BaseModel

from src.analysis_service.rabbitmq_consumer import RabbitMQConsumerConfig
from src.shared.config import MinIOConfig, AnalysisCompletedPublisherConfig


class RedisConfig(BaseModel):
    host: str
    port: int
    db: int
    password: Optional[str] = None
    ttl: int


class LLMConfig(BaseModel):
    api_key: Optional[str] = None
    model: str = "gpt-5-mini"
    base_url: str = "https://api.openai.com/v1"
    timeout: float = 30.0


class AnalysisServiceConfig(BaseModel):
    consumer: RabbitMQConsumerConfig
    publisher: AnalysisCompletedPublisherConfig
    mongo_uri: str
    mongo_db_name: str
    redis: RedisConfig
    llm_prompt_id: str
    llm: LLMConfig


def load_config() -> AnalysisServiceConfig:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASS", "guest")

    transcript_created_queue = os.getenv("TRANSCRIPT_CREATED_QUEUE", "transcript.created")
    analysis_completed_queue = os.getenv("ANALYSIS_COMPLETED_QUEUE", "analysis.completed")

    mongo_uri = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
    mongo_db_name = os.getenv("MONGO_DB", "therapy_analysis")

    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    redis_password = os.getenv("REDIS_PASSWORD", None)
    redis_ttl = int(os.getenv("REDIS_TTL", "3600"))

    llm_prompt_id = os.getenv("LLM_PROMPT_ID", "v1")

    llm_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    llm_model = os.getenv("LLM_MODEL", "gpt-5-mini")
    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_timeout = float(os.getenv("LLM_TIMEOUT", "6000.0"))

    consumer_config = RabbitMQConsumerConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=transcript_created_queue,
    )

    publisher_config = AnalysisCompletedPublisherConfig(
        host=host,
        port=port,
        username=user,
        password=password,
        queue_name=analysis_completed_queue,
    )

    redis_config = RedisConfig(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        ttl=redis_ttl,
    )

    llm_config = LLMConfig(
        api_key=llm_api_key,
        model=llm_model,
        base_url=llm_base_url,
        timeout=llm_timeout,
    )

    return AnalysisServiceConfig(
        consumer=consumer_config,
        publisher=publisher_config,
        mongo_uri=mongo_uri,
        mongo_db_name=mongo_db_name,
        redis=redis_config,
        llm_prompt_id=llm_prompt_id,
        llm=llm_config,
    )
