import pytest
from src.analysis_service.run_worker import main
from src.analysis_service.llm_backend import LLMAnalysisBackend
from src.analysis_service.redis_client import RedisClient

@pytest.mark.unit
def test_should_wire_with_llm_backend_and_redis(mocker):
    # Mock all external dependencies
    mock_load_config = mocker.patch("src.analysis_service.run_worker.load_config")
    mock_minio_config = mocker.patch("src.analysis_service.run_worker.get_minio_config")
    mock_minio_storage = mocker.patch("src.analysis_service.run_worker.MinioStorage")
    mock_mongo_client = mocker.patch("src.analysis_service.run_worker.MongoClient")
    mock_videos_repo = mocker.patch("src.analysis_service.run_worker.MongoVideosRepository")
    mock_analysis_repo = mocker.patch("src.analysis_service.run_worker.MongoAnalysisRepository")
    mock_publisher = mocker.patch("src.analysis_service.run_worker.RabbitMQAnalysisEventPublisher")
    mock_consumer = mocker.patch("src.analysis_service.run_worker.RabbitMQTranscriptCreatedConsumer")
    
    # Mock Redis and LLM Backend
    mock_redis_client_class = mocker.patch("src.analysis_service.run_worker.RedisClient")
    mock_llm_backend_class = mocker.patch("src.analysis_service.run_worker.LLMAnalysisBackend")
    mock_llm_client_factory = mocker.patch("src.analysis_service.run_worker.get_llm_client")

    # Setup config
    mock_config = mocker.MagicMock()
    mock_config.redis.host = "redis-host"
    mock_config.redis.port = 6379
    mock_config.redis.db = 0
    mock_config.redis.password = "secret"
    mock_config.redis.ttl = 3600
    mock_config.llm_prompt_id = "v1"
    mock_config.llm.api_key = "test-key"
    mock_config.llm.model = "gemini-2.5-flash"
    mock_config.llm.base_url = "https://generativelanguage.googleapis.com"
    mock_config.llm.timeout = 180.0
    mock_load_config.return_value = mock_config

    mock_consumer.return_value.run_forever.side_effect = Exception("Stop execution")
    
    try:
        main()
    except Exception as e:
        if str(e) != "Stop execution":
            raise e

    mock_redis_client_class.assert_called_once_with(
        host="redis-host",
        port=6379,
        db=0,
        password="secret"
    )
    
    mock_llm_client_factory.assert_called_once_with(
        api_key="test-key",
        model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com",
        timeout=180.0
    )
    
    mock_llm_backend_class.assert_called_once_with(
        llm_client=mock_llm_client_factory.return_value,
        redis_cache=mock_redis_client_class.return_value,
        cache_ttl_seconds=3600,
        prompt_id="v1"
    )
    
    mock_consumer.assert_called_once()
    args, kwargs = mock_consumer.call_args
    assert kwargs["backend"] == mock_llm_backend_class.return_value
