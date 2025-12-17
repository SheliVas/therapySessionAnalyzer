import pytest
from unittest.mock import MagicMock
from src.analysis_service.redis_client import RedisClient

@pytest.fixture
def mock_redis(mocker):
    return mocker.patch("redis.Redis")

@pytest.mark.unit
def test_should_set_value_with_ttl_when_called(mock_redis):
    client = RedisClient(host="localhost", port=6379, db=0)
    client.set("key", {"data": "value"}, ttl_seconds=60)
    
    mock_redis.return_value.setex.assert_called_once()

@pytest.mark.unit
def test_should_get_value_when_exists(mock_redis):
    mock_redis.return_value.get.return_value = b'{"data": "value"}'
    client = RedisClient(host="localhost", port=6379, db=0)
    
    result = client.get("key")
    
    assert result == {"data": "value"}

@pytest.mark.unit
def test_should_return_none_when_key_missing(mock_redis):
    mock_redis.return_value.get.return_value = None
    client = RedisClient(host="localhost", port=6379, db=0)
    
    result = client.get("missing_key")
    
    assert result is None

@pytest.mark.unit
def test_should_raise_error_on_connection_failure(mock_redis):
    import redis
    mock_redis.return_value.get.side_effect = redis.exceptions.ConnectionError("Connection refused")
    client = RedisClient(host="localhost", port=6379, db=0)
    
    with pytest.raises(redis.exceptions.ConnectionError):
        client.get("key")
