import time
import json
from typing import Dict, Tuple, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import iterate_in_threadpool

# In-memory fallback: { key: (expiry_timestamp, status_code, JSON_body) }
_memory_cache: Dict[str, Tuple[float, int, Any]] = {}
CACHE_TTL = 300  # 5 minutes


def _cache_get(key: str) -> Tuple[float, int, Any] | None:
    """Try Redis first, fall back to in-memory cache."""
    try:
        from src.utils.redis_client import cache_get as redis_get
        raw = redis_get(f"idempotency:{key}")
        if raw is not None:
            return (raw["expiry"], raw["status_code"], raw["body"])
    except Exception:
        pass
    return _memory_cache.get(key)


def _cache_set(key: str, value: Tuple[float, int, Any]) -> None:
    """Try Redis first, fall back to in-memory cache."""
    try:
        from src.utils.redis_client import cache_set as redis_set
        expiry, status_code, body = value
        redis_set(f"idempotency:{key}", {"expiry": expiry, "status_code": status_code, "body": body}, ttl=CACHE_TTL)
    except Exception:
        pass
    _memory_cache[key] = value


def clean_expired_keys():
    now = time.time()
    expired = [k for k, v in _memory_cache.items() if v[0] < now]
    for k in expired:
        _memory_cache.pop(k, None)


async def idempotency_middleware(request: Request, call_next) -> Response:
    """Middleware to intercept and cache idempotent mutation requests."""
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return await call_next(request)

    key = request.headers.get("Idempotency-Key")
    if not key:
        return await call_next(request)

    clean_expired_keys()
    now = time.time()

    cached = _cache_get(key)
    if cached is not None:
        expiry, status_code, body = cached
        if expiry > now:
            return JSONResponse(
                status_code=status_code,
                content=body,
                headers={"X-Cache-Lookup": "HIT", "X-Idempotency-Key": key}
            )

    response = await call_next(request)

    if response.status_code < 500:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            response_body = [chunk async for chunk in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(response_body))

            try:
                body_bytes = b"".join(response_body)
                body_json = json.loads(body_bytes.decode("utf-8"))
                _cache_set(key, (now + CACHE_TTL, response.status_code, body_json))
            except Exception:
                pass

    return response
