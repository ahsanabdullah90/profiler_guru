import bcrypt
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.utils.config import config
from src.utils.logger import logger
from src.api.api_dependencies import create_jwt_token, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    password: str

class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    if not config.APP_PASSWORD:
        raise HTTPException(status_code=500, detail="Application password not configured in .env")

    try:
        is_bcrypt = (
            config.APP_PASSWORD.startswith(("$2a$", "$2b$", "$2y$"))
            and len(config.APP_PASSWORD) == 60
        )

        if is_bcrypt:
            authenticated = bcrypt.checkpw(
                req.password.encode("utf-8"),
                config.APP_PASSWORD.encode("utf-8")
            )
        else:
            authenticated = (req.password == config.APP_PASSWORD)

        if not authenticated:
            raise HTTPException(status_code=401, detail="Incorrect password")

        token = create_jwt_token()
        return TokenResponse(token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail="Error verifying password")

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(current_user: dict = Depends(get_current_user)):
    """Issue a new token before the current one expires (sliding session)."""
    token = create_jwt_token()
    return TokenResponse(token=token)

@router.get("/verify")
def verify_token(current_user: dict = Depends(get_current_user)):
    """Used by the frontend to check if the current token is still valid on boot."""
    return {"status": "valid"}
