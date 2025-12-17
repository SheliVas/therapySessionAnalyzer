from typing import Protocol, Any, Optional


class RedisCache(Protocol):
    """Protocol for Redis cache operations."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: The cache key.
        
        Returns:
            The cached value, or None if not found.
        """
        ...
    
    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set value in cache with TTL.
        
        Args:
            key: The cache key.
            value: The value to cache.
            ttl_seconds: Time to live in seconds.
        """
        ...
