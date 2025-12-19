import logging
from typing import TypeVar, Callable, Any, Optional
from src.analysis_service.redis_cache import RedisCache

logger = logging.getLogger(__name__)

T = TypeVar("T")

def execute_cached_operation(
    cache: RedisCache,
    cache_key: str,
    ttl_seconds: int,
    operation: Callable[[], Any],
    validator: Optional[Callable[[Any], T]] = None,
) -> T:
    """Execute an operation with Redis caching and optional validation.
    
    Args:
        cache: The Redis cache instance.
        cache_key: The key to use for caching.
        ttl_seconds: Time to live for the cached value.
        operation: The function to execute if cache miss.
        validator: Optional function to validate/transform the result (from cache or operation).
        
    Returns:
        The result (validated if validator provided).
    """
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info("cache.hit key=%s", cache_key)
        if validator:
            return validator(cached)
        return cached  # type: ignore

    logger.info("cache.miss key=%s", cache_key)
    result = operation()
    
    if validator:
        result = validator(result)
        
    cache.set(cache_key, result, ttl_seconds)
    logger.info("cache.store key=%s ttl=%d", cache_key, ttl_seconds)
    return result
