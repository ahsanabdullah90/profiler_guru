import time
from typing import Dict, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.utils.config import config
from src.utils.logger import logger

security = HTTPBearer(auto_error=False)

# Routes that do not require JWT authentication
PUBLIC_ROUTES: set[tuple[str, str]] = {
    ("POST", "/api/auth/login"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("GET", "/api/health"),
    ("GET", "/api/status"),
    ("GET", "/api/v1/status"),
    ("POST", "/api/v1/logs/frontend"),
    ("POST", "/api/v1/whatsapp/ingest"),
    ("GET", "/api/v1/whatsapp/status"),
}

# Path prefixes that are always public (e.g. WebSocket upgrade paths)
PUBLIC_PREFIXES: tuple[str, ...] = (
    "/ws/",
    "/static/",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def create_jwt_token() -> str:
    """Issues a short-lived JWT for portal session authentication."""
    payload: Dict[str, Any] = {
        "sub": "portal",
        "iat": int(time.time()),
        "exp": int(time.time()) + config.JWT_EXPIRY_HOURS * 3600,
        "jti": str(int(time.time() * 1_000_000)),
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token. Raises on expiry or tampering."""
    try:
        return jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """FastAPI dependency that extracts and validates the JWT from the Authorization header."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_jwt_token(credentials.credentials)


def is_public_path(method: str, path: str) -> bool:
    """Returns True if the given method+path is publicly accessible without a JWT."""
    if (method, path) in PUBLIC_ROUTES:
        return True
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    return False
