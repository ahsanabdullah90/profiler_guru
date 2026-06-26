import os
import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Set

from src.utils.config import config
from src.utils.logger import logger
from src.utils.task_tracker import task_tracker
from src.utils.ollama_client import ollama_client
from src.engine.settings_manager import settings_manager

# Import routers
from src.api.api_auth import router as auth_router
from src.api.api_instagram import router as instagram_router, get_status as get_ig_status
from src.api.api_contacts import router as contacts_router
from src.api.api_rag import router as rag_router
from src.api.api_reports import router as reports_router
from src.api.api_settings import router as settings_router
from src.api.state import sync_engine

app = FastAPI(
    title="Profile_Guru API",
    description="High-Performance Decoupled Backend for Profile_Guru",
    version="1.0.0"
)

# CORS configuration to allow access from Next.js on port 3000 (loopback and local network)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Lightweight health-check endpoint — used by run.bat to confirm the server is
# fully up before opening the browser. Excluded from Swagger docs.
@app.get("/api/health", include_in_schema=False)
def health_check():
    return {"status": "ok", "version": "1.0.0"}

# GET status fallback endpoint — used by the frontend to poll for system status
# when WebSockets are blocked by browser extensions, adblockers, or strict firewalls.
@app.get("/api/status")
def get_system_status():
    # 1. Check Ollama status (non-blocking)
    try:
        ollama_online = False
        models = ollama_client.get_installed_models()
        if models is not None:
            ollama_online = True
    except Exception:
        ollama_online = False
        
    # 2. Check Online LLM status
    online_llm_active = bool(config.GOOGLE_API_KEY or config.CLOUD_API_KEY)
    
    # 3. Fetch task progress from task_tracker
    active_tasks = task_tracker.get_active_tasks()
    
    # 4. Extract specific tasks (Sync, Transcription, RAG indexing)
    sync_status = {"status": "idle", "contact": "", "current": 0, "total": 0}
    transcription_status = {"status": "idle", "contact": "", "current": 0, "total": 0}
    rag_status = {"status": "idle", "contact": "", "progress": 100}
    
    for task in active_tasks:
        tid = task.get("id", "")
        current = task.get("current", 0)
        total = task.get("total", 0)
        
        if tid == "instagram_sync":
            syncing_contacts = list(sync_engine.active_syncs)
            contact_name = syncing_contacts[0] if syncing_contacts else "Direct Messages"
            sync_status = {
                "status": "syncing",
                "contact": contact_name,
                "current": current,
                "total": total
            }
        elif tid == "backfill_historical":
            rag_status = {
                "status": "indexing",
                "contact": "Historical Backfill",
                "progress": int((current / total * 100)) if total > 0 else 0
            }
        elif tid.startswith("transcribe_"):
            contact_name = tid.replace("transcribe_", "")
            transcription_status = {
                "status": "transcribing",
                "contact": contact_name,
                "current": current,
                "total": total
            }
            
    # Check if there are any active syncs that didn't get registered as a task yet
    if sync_status["status"] == "idle" and sync_engine.active_syncs:
        sync_status = {
            "status": "syncing",
            "contact": list(sync_engine.active_syncs)[0],
            "current": 0,
            "total": 0
        }
        
    return {
        "app_online": True,
        "instagram_sync": sync_status,
        "transcription": transcription_status,
        "rag": rag_status,
        "online_llm": {
            "model": "Gemini 1.5 Flash",
            "online": online_llm_active
        },
        "ollama": {
            "model": settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL),
            "online": ollama_online
        }
    }


# Include Routers
app.include_router(auth_router)
app.include_router(instagram_router)
app.include_router(contacts_router)
app.include_router(rag_router)
app.include_router(reports_router)
app.include_router(settings_router)

# Secure local audio stream endpoint to protect privacy
@app.get("/static/audio/{contact}/{filename}")
def get_audio_file(contact: str, filename: str):
    file_path = Path(config.CHATS_DIR) / contact / "Audio" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(file_path))

# WebSocket Connection Manager for real-time system status broadcasting
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        # Create a list of send tasks to run concurrently
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

@app.websocket("/ws/status")
async def status_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open and listen for messages (ping/pong)
            data = await websocket.receive_text()
            # Respond immediately to client pings
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Background task to broadcast system monitor updates to all connected clients
async def system_status_broadcaster():
    logger.info("Starting background system status broadcaster...")
    
    # Cache provider statuses to avoid aggressive polling
    last_ollama_check = 0.0
    ollama_online = False
    
    while True:
        try:
            if manager.active_connections:
                now = asyncio.get_event_loop().time()
                
                # 1. Check Ollama status (ping every 5 seconds)
                if now - last_ollama_check > 5.0:
                    try:
                        # Lightweight ping to local Ollama port 11434
                        ollama_online = False
                        models = ollama_client.get_installed_models()
                        if models is not None:
                            ollama_online = True
                    except Exception:
                        ollama_online = False
                    last_ollama_check = now
                
                # 2. Check Online LLM status (checks key presence)
                online_llm_active = bool(config.GOOGLE_API_KEY or config.CLOUD_API_KEY)
                
                # 3. Fetch task progress from task_tracker
                active_tasks = task_tracker.get_active_tasks()
                
                # 4. Extract specific tasks (Sync, Transcription, RAG indexing)
                sync_status = {"status": "idle", "contact": "", "current": 0, "total": 0}
                transcription_status = {"status": "idle", "contact": "", "current": 0, "total": 0}
                rag_status = {"status": "idle", "contact": "", "progress": 100}
                
                # Scan active tasks in task_tracker
                for task in active_tasks:
                    tid = task.get("id", "")
                    name = task.get("name", "")
                    current = task.get("current", 0)
                    total = task.get("total", 0)
                    
                    if tid == "instagram_sync":
                        # Instagram sync is active
                        # Find which contact is syncing
                        syncing_contacts = list(sync_engine.active_syncs)
                        contact_name = syncing_contacts[0] if syncing_contacts else "Direct Messages"
                        sync_status = {
                            "status": "syncing",
                            "contact": contact_name,
                            "current": current,
                            "total": total
                        }
                    elif tid == "backfill_historical":
                        rag_status = {
                            "status": "indexing",
                            "contact": "Historical Backfill",
                            "progress": int((current / total * 100)) if total > 0 else 0
                        }
                    elif tid.startswith("transcribe_"):
                        # Transcription task active
                        contact_name = tid.replace("transcribe_", "")
                        transcription_status = {
                            "status": "transcribing",
                            "contact": contact_name,
                            "current": current,
                            "total": total
                        }
                        
                # Check if there are any active syncs that didn't get registered as a task yet
                if sync_status["status"] == "idle" and sync_engine.active_syncs:
                    sync_status = {
                        "status": "syncing",
                        "contact": list(sync_engine.active_syncs)[0],
                        "current": 0,
                        "total": 0
                    }
                
                # Compile final status packet
                status_packet = {
                    "type": "status_update",
                    "app_online": True,
                    "instagram_sync": sync_status,
                    "transcription": transcription_status,
                    "rag": rag_status,
                    "online_llm": {
                        "model": "Gemini 1.5 Flash",
                        "online": online_llm_active
                    },
                    "ollama": {
                        "model": settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL),
                        "online": ollama_online
                    }
                }
                
                await manager.broadcast(status_packet)
                
        except Exception as e:
            logger.error(f"Error in status broadcaster loop: {e}")
            
        await asyncio.sleep(2.0)

@app.on_event("startup")
async def startup_event():
    # Start the background broadcaster task
    asyncio.create_task(system_status_broadcaster())
    
    # Try restoring Instagram session silently on boot
    session_file = sync_engine.session_path
    if os.path.exists(session_file):
        logger.info("Restoring Instagram login session on backend startup...")
        def run_restore():
            try:
                sync_engine.login(None, None)
            except Exception as e:
                logger.error(f"Failed to restore login session: {e}")
        asyncio.get_event_loop().run_in_executor(None, run_restore)

if __name__ == "__main__":
    config.validate()
    logger.info("Starting FastAPI Server...")
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=False)

