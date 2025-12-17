import json
from typing import Any, Optional
import redis
from src.analysis_service.redis_cache import RedisCache

class RedisClient(RedisCache):
    """Redis client implementation of RedisCache."""
    
    def __init__(self, host: str, port: int, db: int, password: Optional[str] = None):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=False
        )

    def get(self, key: str) -> Optional[Any]:
        data = self.client.get(key)
        if data is None:
            return None
        return json.loads(data.decode("utf-8"))

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        data = json.dumps(value)
        self.client.setex(key, ttl_seconds, data)
