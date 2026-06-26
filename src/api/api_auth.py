from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import bcrypt
from src.utils.config import config
from src.utils.logger import logger

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    password: str

@router.post("/login")
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
            
        if authenticated:
            return {"status": "success", "token": "session_active"}
        else:
            raise HTTPException(status_code=401, detail="Incorrect password")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail="Error verifying password")
