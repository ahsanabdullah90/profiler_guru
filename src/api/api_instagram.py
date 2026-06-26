import threading
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from src.utils.config import config
from src.utils.logger import logger
from src.api.state import sync_engine, sync_manager

router = APIRouter(prefix="/api/instagram", tags=["Instagram"])

# Module-level variable to cache active challenge URLs
challenge_url = None

class LoginRequest(BaseModel):
    username: str
    password: str

class TwoFactorRequest(BaseModel):
    code: str
    username: Optional[str] = None
    password: Optional[str] = None

@router.get("/status")
def get_status():
    global challenge_url
    try:
        # Check if client timeline works as a proxy for active session
        timeline_ok = False
        try:
            if sync_engine.cl.user_id:
                sync_engine.cl.get_timeline_feed()
                timeline_ok = True
        except Exception:
            pass

        logged_in = timeline_ok
        
        return {
            "logged_in": logged_in,
            "username": config.INSTAGRAM_USERNAME or "",
            "active_syncs": list(sync_engine.active_syncs),
            "daemon_sync_active": sync_manager.is_running,
            "challenge_url": challenge_url
        }
    except Exception as e:
        logger.error(f"Error getting Instagram status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
def login(req: LoginRequest):
    global challenge_url
    try:
        status, info = sync_engine.login(req.username, req.password)
        
        if status == "success":
            challenge_url = None
            return {"status": "success"}
        elif status == "2fa_required":
            challenge_url = None
            return {"status": "2fa_required", "info": "Two-Factor Authentication is required."}
        elif status == "challenge":
            challenge_url = info
            return {"status": "challenge", "challenge_url": info}
        else:
            challenge_url = None
            raise HTTPException(status_code=400, detail=f"Login failed: {info}")
    except Exception as e:
        logger.error(f"Error logging in: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/2fa")
def submit_2fa(req: TwoFactorRequest):
    global challenge_url
    try:
        status, info = sync_engine.login(req.username, req.password, verification_code=req.code)
        if status == "success":
            challenge_url = None
            return {"status": "success"}
        else:
            raise HTTPException(status_code=400, detail=f"2FA Verification failed: {info}")
    except Exception as e:
        logger.error(f"Error verifying 2FA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/once")
def trigger_sync(background_tasks: BackgroundTasks):
    try:
        # Verify active session before starting
        timeline_ok = False
        try:
            if sync_engine.cl.user_id:
                sync_engine.cl.get_timeline_feed()
                timeline_ok = True
        except Exception:
            pass

        if not timeline_ok:
            raise HTTPException(status_code=401, detail="Instagram not logged in or session expired")
        
        # Trigger the fetch in a background thread to prevent blocking
        background_tasks.add_task(sync_engine.fetch_new_messages)
        return {"status": "started"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error triggering sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/toggle")
def toggle_daemon():
    try:
        if sync_manager.is_running:
            sync_manager.stop()
            active = False
        else:
            # Verify session first
            timeline_ok = False
            try:
                if sync_engine.cl.user_id:
                    sync_engine.cl.get_timeline_feed()
                    timeline_ok = True
            except Exception:
                pass

            if not timeline_ok:
                raise HTTPException(status_code=401, detail="Instagram not logged in or session expired")

            sync_manager.start()
            active = True
            
        return {"daemon_sync_active": active}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error toggling background sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))
