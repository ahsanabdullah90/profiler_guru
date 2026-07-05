"""
Redis client with graceful fallback and connection pooling.

If Redis is unavailable or REDIS_ENABLED=false, all cache operations become no-ops.
The app continues working without caching — Redis is purely an optimization layer.
"""

import json
import os
import threading
from typing import Any

from src.utils.logger import logger

REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "300"))  # 5 minutes default

_pool = None
_redis_client = None
_redis_available = False
_init_lock = threading.Lock()


def _get_client():
    """Lazy-initialize Redis connection with pooling and reconnection."""
    global _pool, _redis_client, _redis_available
    if not REDIS_ENABLED:
        return None

    # Fast path: existing working connection
    if _redis_client is not None and _redis_available:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception as e:
            logger.warning(f"Redis ping failed, resetting connection: {e}")
            _redis_available = False
            _redis_client = None
            # Reset pool on connection failure
            _pool = None

    # Slow path: create new connection (thread-safe)
    with _init_lock:
        # Double-check after acquiring lock
        if _redis_client is not None and _redis_available:
            return _redis_client
        try:
            import redis
            if _pool is None:
                _pool = redis.ConnectionPool.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    max_connections=5,
                )
            _redis_client = redis.Redis(connection_pool=_pool)
            _redis_client.ping()
            _redis_available = True
            logger.info("Redis connected successfully")
            return _redis_client
        except Exception as e:
            _redis_available = False
            _pool = None
            _redis_client = None
            logger.warning(f"Redis unavailable, caching disabled: {e}")
            return None


def cache_get(key: str) -> Any | None:
    """Get a cached value. Returns None if miss or Redis unavailable."""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        # Connection might have dropped — reset state
        logger.debug(f"Redis cache_get failed for key '{key}' — resetting connection")
        _reset_connection()
        return None


def cache_set(key: str, value: Any, ttl: int = CACHE_TTL) -> bool:
    """Set a cached value with TTL. Returns True on success."""
    client = _get_client()
    if client is None:
        return False
    try:
        client.set(key, json.dumps(value, default=str), ex=ttl)
        return True
    except Exception:
        _reset_connection()
        logger.debug(f"Redis cache_set failed for key '{key}' — resetting connection")
        return False


def cache_delete(key: str) -> bool:
    """Delete a cached key. Returns True on success."""
    client = _get_client()
    if client is None:
        return False
    try:
        client.delete(key)
        return True
    except Exception:
        _reset_connection()
        logger.debug(f"Redis cache_delete failed for key '{key}' — resetting connection")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count of deleted keys."""
    client = _get_client()
    if client is None:
        return 0
    try:
        keys = list(client.scan_iter(match=pattern, count=100))
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Redis cache_delete_pattern failed for pattern '{pattern}': {e}")
        _reset_connection()
        return 0


def cache_ping() -> bool:
    """Check if Redis is reachable."""
    client = _get_client()
    if client is None:
        return False
    try:
        return client.ping()
    except Exception:
        _reset_connection()
        return False


def _reset_connection():
    """Reset connection state on error — next call will reconnect."""
    global _redis_client, _redis_available, _pool
    _redis_client = None
    _redis_available = False
    _pool = None


def invalidate_contacts_cache() -> None:
    """Invalidate all contacts-related caches. Call after sync/import."""
    cache_delete("contacts:list:all")
    cache_delete("contacts:index_counts")
    cache_delete_pattern("analytics:*")
