import os
import pytest
from src.analysis_service.config import load_config

@pytest.mark.unit
def test_should_load_analysis_config_from_env_vars(mocker):
    mocker.patch.dict(os.environ, {
        "MONGO_URI": "mongodb://mongo:27017",
        "MONGO_DB": "analysis-db",
        "REDIS_HOST": "redis-host",
        "REDIS_PORT": "6380",
        "REDIS_DB": "1",
        "REDIS_PASSWORD": "secret-redis",
        "REDIS_TTL": "7200",
        "LLM_PROMPT_ID": "v2",
        "GEMINI_API_KEY": "test-api-key"
    })
    
    config = load_config()
    
    assert config.mongo_uri == "mongodb://mongo:27017"
    assert config.mongo_db_name == "analysis-db"
    assert config.redis.host == "redis-host"
    assert config.redis.port == 6380
    assert config.redis.db == 1
    assert config.redis.password == "secret-redis"
    assert config.redis.ttl == 7200
    assert config.llm_prompt_id == "v2"
