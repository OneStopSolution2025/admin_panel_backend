import redis
from redis import Redis
from typing import Optional
import logging
import json

# Fixed import - no 'app.' prefix
from core.config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """Redis cache manager"""
    
    def __init__(self):
        self.client: Optional[Redis] = None
    
    def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info("✅ Redis connection established")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {str(e)}")
            logger.warning("Continuing without cache...")
            self.client = None
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.client:
            return None
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Cache GET error: {str(e)}")
            return None
    
    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache"""
        if not self.client:
            return False
        try:
            self.client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Cache SET error: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.client:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error: {str(e)}")
            return False
    
    def close(self):
        """Close Redis connection"""
        if self.client:
            try:
                self.client.close()
                logger.info("✅ Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis: {str(e)}")

# Global cache instance
cache = CacheManager()
