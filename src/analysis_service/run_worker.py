from pymongo import MongoClient

from src.analysis_service.config import load_config
from src.analysis_service.mongo_repository import MongoAnalysisRepository
from src.analysis_service.rabbitmq_consumer import RabbitMQTranscriptCreatedConsumer
from src.analysis_service.rabbitmq_publisher import RabbitMQAnalysisEventPublisher
from src.analysis_service.redis_client import RedisClient
from src.analysis_service.llm_client import get_llm_client
from src.analysis_service.llm_backend import LLMAnalysisBackend
from src.shared.minio_storage import MinioStorage
from src.shared.videos_repository import MongoVideosRepository
from src.shared.config import get_minio_config


def main() -> None:
    config = load_config()
    minio_config = get_minio_config()
    storage_client = MinioStorage(minio_config)

    mongo_client = MongoClient(config.mongo_uri)
    videos_repository = MongoVideosRepository(mongo_client, db_name=config.mongo_db_name)
    repository = MongoAnalysisRepository(mongo_client, db_name=config.mongo_db_name)

    redis_client = RedisClient(
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
        password=config.redis.password,
    )
    llm_client = get_llm_client(
        api_key=config.llm.api_key,
        model=config.llm.model,
        base_url=config.llm.base_url,
        timeout=config.llm.timeout,
    )
    backend = LLMAnalysisBackend(
        llm_client=llm_client,
        redis_cache=redis_client,
        cache_ttl_seconds=config.redis.ttl,
        prompt_id=config.llm_prompt_id,
    )
    
    publisher = RabbitMQAnalysisEventPublisher(config.publisher)

    consumer = RabbitMQTranscriptCreatedConsumer(
        config=config.consumer,
        backend=backend,
        publisher=publisher,
        repository=repository,
        storage_client=storage_client,
        videos_repository=videos_repository,
    )

    consumer.run_forever()


if __name__ == "__main__":
    main()
