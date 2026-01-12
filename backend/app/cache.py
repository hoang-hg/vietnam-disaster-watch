import time
import json
import logging
from collections import OrderedDict
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
        self.memory_cache = OrderedDict()
        self.capacity = 1000 
        
        redis_url = getattr(settings, "redis_url", None)
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True) # Automatically decode to strings
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
                pass # Fallback to memory on Redis error
        
        # 2. Fallback to local memory (Per-worker cache)
        if key in self.memory_cache:
            val, expiry = self.memory_cache[key]
            if time.time() < expiry:
                # [FIX] Move to end to mark as recently used (True LRU)
                self.memory_cache.move_to_end(key)
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

        # 2. Store in local memory with LRU-like eviction
        if key in self.memory_cache:
            self.memory_cache.move_to_end(key)
        self.memory_cache[key] = (value, time.time() + ttl)
        
        if len(self.memory_cache) > self.capacity:
            self.memory_cache.popitem(last=False)

    def delete(self, key: str):
        # 1. Delete from Redis
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis delete failed: {e}")
        
        # 2. Delete from local memory
        if key in self.memory_cache:
            del self.memory_cache[key]

    def delete_match(self, pattern: str):
        """Delete all keys matching the glob pattern (e.g. 'stats_*')"""
        import fnmatch
        
        # 1. Redis
        if self.redis_client:
            try:
                # Use SCAN to find keys non-blocking
                # Use SCAN ITER for safer, simpler iteration
                for key in self.redis_client.scan_iter(match=pattern, count=100):
                    self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis delete_match failed: {e}")

        # 2. Local Memory
        # Create list of keys to delete to avoid runtime error during iteration
        to_delete = [k for k in self.memory_cache if fnmatch.fnmatch(k, pattern)]
        for k in to_delete:
            del self.memory_cache[k]

    def acquire_lock(self, lock_name: str, timeout: int = 600) -> bool:
        """
        Try to acquire a distributed lock.
        Returns True if acquired, False if already locked by another worker.
        """
        lock_key = f"lock:{lock_name}"
        
        # 1. Redis Lock (Preferred)
        if self.redis_client:
            try:
                # set(nx=True) returns True if set happened, None/False otherwise
                acquired = self.redis_client.set(lock_key, "locked", nx=True, ex=timeout)
                return bool(acquired)
            except Exception as e:
                logger.error(f"Redis lock acquisition failed: {e}")
                return False # Fail safe: don't run if Redis error to avoid stampede? Or True? 
                # Let's return False to be safe in Prod. But wait, if Redis is down, nothing updates.
                # Actually, duplicate crawling is better than NO crawling in critical times. 
                # But multiple workers hammering usually is bad. Let's return False for now assuming Redis is stable.
        
        # 2. Memory Lock (Fallback for single-process/dev)
        # Note: This only works within ONE process. If multi-worker without Redis, this invalid.
        # But usually Multi-worker implies Redis is available in our setup.
        now = time.time()
        if lock_key in self.memory_cache:
            _, expiry = self.memory_cache[lock_key]
            if now < expiry:
                return False # Already locked
        
        # Acquire
        self.memory_cache[lock_key] = ("locked", now + timeout)
        return True

    def release_lock(self, lock_name: str):
        lock_key = f"lock:{lock_name}"
        if self.redis_client:
            try:
                self.redis_client.delete(lock_key)
            except Exception as e:
                logger.error(f"Redis unlock failed: {e}")
        
        if lock_key in self.memory_cache:
            del self.memory_cache[lock_key]

# Singleton instance
cache = CacheManager()
