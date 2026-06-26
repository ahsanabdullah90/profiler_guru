import time
import json
from typing import Dict, Tuple, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import iterate_in_threadpool

# Cache: { key: (expiry_timestamp, status_code, JSON_body) }
_idempotency_cache: Dict[str, Tuple[float, int, Any]] = {}
CACHE_TTL = 300  # 5 minutes

def clean_expired_keys():
    now = time.time()
    expired = [k for k, v in _idempotency_cache.items() if v[0] < now]
    for k in expired:
        _idempotency_cache.pop(k, None)

async def idempotency_middleware(request: Request, call_next) -> Response:
    """Middleware to intercept and cache idempotent mutation requests."""
    # Only apply to mutations
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return await call_next(request)

    # Check for the header
    key = request.headers.get("Idempotency-Key")
    if not key:
        return await call_next(request)

    # Clean up expired keys
    clean_expired_keys()
    now = time.time()

    # If key is in cache and not expired, return the cached response
    if key in _idempotency_cache:
        expiry, status_code, body = _idempotency_cache[key]
        if expiry > now:
            return JSONResponse(
                status_code=status_code,
                content=body,
                headers={"X-Cache-Lookup": "HIT", "X-Idempotency-Key": key}
            )

    # Execute the request
    response = await call_next(request)

    # Only cache successful or client-error responses (status < 500)
    if response.status_code < 500:
        # Check if it is a JSON response
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            # Consume response body safely
            response_body = [chunk async for chunk in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(response_body))
            
            try:
                body_bytes = b"".join(response_body)
                body_json = json.loads(body_bytes.decode("utf-8"))
                # Store in cache
                _idempotency_cache[key] = (now + CACHE_TTL, response.status_code, body_json)
            except Exception:
                # If parsing fails, do not cache
                pass

    return response
