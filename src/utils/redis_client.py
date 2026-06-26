"""
Redis client with graceful fallback.

If Redis is unavailable or REDIS_ENABLED=false, all cache operations become no-ops.
The app continues working without caching — Redis is purely an optimization layer.
"""

import json
import os
from typing import Any, Optional

from src.utils.logger import logger

REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "300"))  # 5 minutes default

_redis_client = None
_redis_available = False


def _get_client():
    """Lazy-initialize Redis connection. Returns None if unavailable."""
    global _redis_client, _redis_available
    if not REDIS_ENABLED:
        return None
    if _redis_client is not None and _redis_available:
        return _redis_client
    try:
        import redis
        _redis_client = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _redis_client.ping()
        _redis_available = True
        return _redis_client
    except Exception as e:
        _redis_available = False
        logger.warning(f"Redis unavailable, caching disabled: {e}")
        return None


def cache_get(key: str) -> Optional[Any]:
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
        return None


def cache_set(key: str, value: Any, ttl: int = CACHE_TTL) -> bool:
    """Set a cached value with TTL. Returns True on success."""
    client = _get_client()
    if client is None:
        return False
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception:
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
    except Exception:
        return 0


def cache_ping() -> bool:
    """Check if Redis is reachable."""
    client = _get_client()
    if client is None:
        return False
    try:
        return client.ping()
    except Exception:
        return False


def invalidate_contacts_cache() -> None:
    """Invalidate all contacts-related caches. Call after sync/import."""
    cache_delete("contacts:list:all")
    cache_delete("contacts:index_counts")
    cache_delete_pattern("analytics:*")
