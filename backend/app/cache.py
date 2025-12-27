import time
import json
import logging
from typing import Any, Optional
from .settings import settings

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class CacheManager:
    """
    Multi-level Cache Manager (Redis with In-Memory fallback).
    Designed to handle high concurrency (10,000+ users).
    """
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}
        
        # Try to initialize Redis if URL is provided
        redis_url = getattr(settings, "redis_url", None)
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False) # Store bytes/pickled for complex objects if needed, but we prefer JSON for cross-platform
                # Test connection
                self.redis_client.ping()
                logger.info("Connected to Redis for high-performance caching.")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}. Falling back to In-Memory cache.")
                self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        # 1. Try Redis first (Shared cache across workers)
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                if val:
                    # If it's a simple string or JSON, we might need decoding logic 
                    # For simplicity in this app, we'll assume we store JSON
                    return json.loads(val)
            except Exception:
                return None
        
        # 2. Fallback to local memory (Per-worker cache)
        if key in self.memory_cache:
            val, expiry = self.memory_cache[key]
            if time.time() < expiry:
                return val
            else:
                del self.memory_cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 300):
        # 1. Store in Redis
        if self.redis_client:
            try:
                # Value must be serializable
                self.redis_client.setex(key, ttl, json.dumps(value))
                return
            except Exception as e:
                logger.error(f"Redis set failed: {e}")

        # 2. Store in local memory
        self.memory_cache[key] = (value, time.time() + ttl)

# Singleton instance
cache = CacheManager()
