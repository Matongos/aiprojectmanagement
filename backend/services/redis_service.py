import redis
from typing import Optional, Any, Dict
from config import settings
import logging
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

class RedisService:
    _instance = None
    _redis_client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._redis_client:
            self._initialize_connection()

    def _initialize_connection(self) -> None:
        """Initialize Redis connection with retries and fallback"""
        try:
            # Ensure Redis settings are available
            redis_host = getattr(settings, 'REDIS_HOST', os.getenv('REDIS_HOST', 'localhost'))
            redis_port = int(getattr(settings, 'REDIS_PORT', os.getenv('REDIS_PORT', '6379')))
            redis_db = int(getattr(settings, 'REDIS_DB', os.getenv('REDIS_DB', '0')))
            redis_password = getattr(settings, 'REDIS_PASSWORD', os.getenv('REDIS_PASSWORD', None))

            self._redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_timeout=1,
                socket_connect_timeout=1,
                retry_on_timeout=True
            )
            # Test connection
            self._redis_client.ping()
            logger.info(f"Successfully connected to Redis at {redis_host}:{redis_port}")
        except (redis.ConnectionError, redis.RedisError) as e:
            logger.warning(f"Could not connect to Redis: {str(e)}. Using in-memory fallback.")
            self._redis_client = self._create_fallback_cache()

    def _create_fallback_cache(self) -> Any:
        """Create an in-memory cache as fallback when Redis is unavailable"""
        class InMemoryCache:
            def __init__(self):
                self._cache = {}
                logger.warning("Using in-memory cache fallback")

            def get(self, key: str) -> Optional[str]:
                if key not in self._cache:
                    return None
                item = self._cache[key]
                if item['expires_at'] and datetime.now() > item['expires_at']:
                    del self._cache[key]
                    return None
                return item['value']

            def setex(self, key: str, time: int, value: str) -> None:
                expires_at = datetime.now() + timedelta(seconds=time)
                self._cache[key] = {
                    'value': value,
                    'expires_at': expires_at
                }

            def delete(self, key: str) -> None:
                self._cache.pop(key, None)

            def ping(self) -> bool:
                return True

        return InMemoryCache()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache with error handling"""
        try:
            value = self._redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting key {key} from Redis: {str(e)}")
            return None

    def setex(self, key: str, time: int, value: Any) -> bool:
        """Set value with expiration and error handling"""
        try:
            serialized_value = json.dumps(value)
            self._redis_client.setex(key, time, serialized_value)
            return True
        except (redis.RedisError, TypeError) as e:
            logger.error(f"Error setting key {key} in Redis: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key with error handling"""
        try:
            self._redis_client.delete(key)
            return True
        except redis.RedisError as e:
            logger.error(f"Error deleting key {key} from Redis: {str(e)}")
            return False

def get_redis_client() -> RedisService:
    """Get Redis service singleton instance"""
    return RedisService() 