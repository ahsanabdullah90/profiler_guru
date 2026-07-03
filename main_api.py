import asyncio
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel

# Import routers
from src.api.api_auth import router as auth_router
from src.api.api_contacts import router as contacts_router
from src.api.api_dependencies import decode_jwt_token, get_current_user, is_public_path
from src.api.api_rag import router as rag_router
from src.api.api_reports import router as reports_router
from src.api.api_settings import router as settings_router
from src.api.api_tasks import router as tasks_router
from src.engine.rag_engine import rag_engine
from src.engine.settings_manager import settings_manager
from src.utils.config import config
from src.utils.idempotency import idempotency_middleware
from src.utils.logger import logger
from src.utils.ollama_client import ollama_client
from src.utils.redis_client import cache_ping as redis_cache_ping
from src.utils.task_tracker import task_tracker
from src.utils.validation import validate_safe_param

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app):
    """Startup/shutdown lifecycle managed by FastAPI."""
    # Startup: launch background tasks
    broadcaster_task = asyncio.create_task(system_status_broadcaster())

    yield  # App is running

    # Shutdown: cancel background tasks
    broadcaster_task.cancel()
    try:
        await broadcaster_task
    except asyncio.CancelledError:
        pass

    logger.info("Shutting down Profile_Guru server...")

    # Close SQLite connection
    try:
        from src.engine.metrics_engine import MetricsEngine
        metrics = MetricsEngine()
        metrics.close()
        logger.info("SQLite connection closed.")
    except Exception as e:
        logger.error(f"Error closing SQLite: {e}")

    # Log completion
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Profile_Guru API",
    description="High-Performance Decoupled Backend for Profile_Guru",
    version="1.0.0",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# CORS — only explicit origins, no wildcard regex
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# -------- Idempotency Key Middleware --------
@app.middleware("http")
async def idempotency_http_middleware(request: Request, call_next):
    return await idempotency_middleware(request, call_next)


# -------- JWT Authentication Middleware --------
@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next):
    """Validates JWT on all /api/* paths except public routes.

    WebSocket paths (/ws/*) and static files (/static/*) are exempt.
    Legacy /api/* paths (without version prefix) are also allowed through
    but emit a deprecation warning log.
    """
    path = request.url.path
    method = request.method

    # Skip non-API paths, public endpoints, and OPTIONS requests
    if method == "OPTIONS" or not path.startswith("/api/") or is_public_path(method, path):
        return await call_next(request)

    # Legacy /api/* (without version) — allow through, log deprecation
    if not path.startswith(API_PREFIX):
        logger.debug(f"Deprecated API path accessed: {method} {path}")

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Not authenticated"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.removeprefix("Bearer ")
    try:
        decode_jwt_token(token)
    except HTTPException:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    response: Response = await call_next(request)
    return response


# -------- Health Check --------
@app.get("/api/health", include_in_schema=False)
def health_check(deep: bool = False):
    if not deep:
        return {"status": "ok", "version": "1.0.0"}

    probes = {}

    # ChromaDB probe
    try:
        count = rag_engine.collection.count()
        probes["chromadb"] = {"status": "ok", "indexed_chunks": count}
    except Exception as e:
        probes["chromadb"] = {"status": "error", "detail": str(e)}

    # Redis probe
    try:
        redis_ok = redis_cache_ping()
        probes["redis"] = {"status": "ok" if redis_ok else "unavailable"}
    except Exception as e:
        probes["redis"] = {"status": "error", "detail": str(e)}

    # Ollama probe
    try:
        models = ollama_client.get_installed_models()
        probes["ollama"] = {"status": "ok", "models": models}
    except Exception as e:
        probes["ollama"] = {"status": "error", "detail": str(e)}

    all_ok = all(p.get("status") == "ok" for p in probes.values())
    return {"status": "ok" if all_ok else "degraded", "version": "1.0.0", "probes": probes}


# -------- GET Status (unauthenticated polling fallback) --------
@app.get("/api/status", include_in_schema=False)
@app.get(f"{API_PREFIX}/status", include_in_schema=False)
def get_system_status():
    """Unauthenticated status polling — delegates to shared payload builder."""
    return _build_status_payload_sync()


# -------- Include Routers (mounted under /api/v1) --------
app.include_router(auth_router)
app.include_router(contacts_router)
app.include_router(rag_router)
app.include_router(reports_router)
app.include_router(settings_router)
app.include_router(tasks_router)




# -------- Frontend error logging --------
class FrontendLogRequest(BaseModel):
    message: str
    stack: str | None = None
    url: str
    timestamp: float
    type: str = "error"

@app.post("/api/v1/logs/frontend", include_in_schema=False)
def log_frontend_error(req: FrontendLogRequest):
    log_msg = f"[Frontend {req.type.upper()}] {req.message} | URL: {req.url} | Client TS: {req.timestamp}"
    if req.stack:
        log_msg += f"\nStack: {req.stack}"
    logger.error(log_msg)
    return {"status": "logged"}


# -------- Audio stream --------
@app.get("/static/audio/{contact}/{filename}")
def get_audio_file(contact: str, filename: str, current_user: dict = Depends(get_current_user)):
    validate_safe_param(contact, "contact")
    validate_safe_param(filename, "filename")
    file_path = Path(config.CHATS_DIR) / contact / "Audio" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(file_path))


# -------- WebSocket Protocol v1 / SSE Shared State --------
_ws_seq_counter = 0
_ws_seq_lock = asyncio.Lock()


async def _next_ws_seq() -> int:
    global _ws_seq_counter
    async with _ws_seq_lock:
        _ws_seq_counter += 1
        return _ws_seq_counter


# -------- Ollama Status Cache (avoids blocking event loop every 2s) --------
_ollama_cache = {"online": False, "last_check": 0.0, "model": ""}
_OLLAMA_CHECK_INTERVAL = 10  # seconds


def _refresh_ollama_cache():
    """Refresh Ollama status cache. Called from thread executor."""
    try:
        models = ollama_client.get_installed_models()
        _ollama_cache["online"] = bool(models)
        _ollama_cache["model"] = settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)
    except Exception:
        _ollama_cache["online"] = False
    _ollama_cache["last_check"] = time.time()


def _build_status_payload_sync() -> dict:
    """Build the shared status payload. Runs in thread executor."""
    # Use cached Ollama status (refreshed every 10s)
    if time.time() - _ollama_cache["last_check"] > _OLLAMA_CHECK_INTERVAL:
        _refresh_ollama_cache()

    online_llm_active = bool(config.GOOGLE_API_KEY or config.CLOUD_API_KEY)
    active_tasks = task_tracker.get_active_tasks()

    transcription_status = {"status": "idle", "contact": "", "current": 0, "total": 0}
    rag_status = {"status": "idle", "contact": "", "progress": 100}

    for task in active_tasks:
        tid = task.get("id", "")
        current = task.get("current", 0)
        total = task.get("total", 0)

        if tid == "backfill_historical":
            rag_status = {
                "status": "indexing",
                "contact": "Historical Backfill",
                "progress": int(current / total * 100) if total > 0 else 0,
            }
        elif tid.startswith("transcribe_"):
            contact_name = tid.replace("transcribe_", "")
            transcription_status = {
                "status": "transcribing",
                "contact": contact_name,
                "current": current,
                "total": total,
            }

    return {
        "app_online": True,
        "transcription": transcription_status,
        "rag": rag_status,
        "online_llm": {
            "model": "Gemini 1.5 Flash",
            "online": online_llm_active,
        },
        "ollama": {
            "model": _ollama_cache["model"],
            "online": _ollama_cache["online"],
        },
    }


async def _build_status_payload() -> dict:
    """Async wrapper — runs sync payload builder in thread executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _build_status_payload_sync)


# ── WebSocket Protocol v1 ──────────────────────────────────────────────────────

@dataclass
class WSClient:
    ws: WebSocket
    channels: set[str] = field(default_factory=lambda: {"status"})
    last_heartbeat: float = field(default_factory=time.time)


class WsManager:
    def __init__(self):
        self.clients: dict[int, WSClient] = {}
        self._id_counter = 0

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    async def add(self, ws: WebSocket) -> int:
        await ws.accept()
        cid = self._next_id()
        self.clients[cid] = WSClient(ws=ws)
        logger.info(f"WS client {cid} connected. Total: {len(self.clients)}")
        return cid

    def remove(self, cid: int):
        self.clients.pop(cid, None)
        logger.info(f"WS client {cid} disconnected. Total: {len(self.clients)}")

    def get(self, cid: int) -> WSClient | None:
        return self.clients.get(cid)

    def subscribed_clients(self, channel: str) -> list[WSClient]:
        return [c for c in self.clients.values() if channel in c.channels]

    async def send_json(self, cid: int, msg: dict) -> bool:
        client = self.clients.get(cid)
        if not client:
            return False
        try:
            await client.ws.send_json(msg)
            return True
        except Exception:
            self.remove(cid)
            return False

    async def broadcast(self, channel: str, msg: dict):
        dead = []
        for cid, client in list(self.clients.items()):
            if channel not in client.channels:
                continue
            try:
                await client.ws.send_json(msg)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.remove(cid)


ws_manager = WsManager()


@app.websocket("/ws/status")
async def status_websocket(websocket: WebSocket):
    cid = await ws_manager.add(websocket)
    client = ws_manager.get(cid)
    assert client is not None

    ping_task = None

    async def heartbeat_loop():
        """Send heartbeat every 15s. Client must respond to keep alive."""
        while True:
            await asyncio.sleep(15)
            now = time.time()
            if now - client.last_heartbeat > 45:
                logger.warning(f"WS client {cid} heartbeat timeout — closing")
                break
            await ws_manager.send_json(cid, {"type": "heartbeat", "ts": now})

    try:
        ping_task = asyncio.create_task(heartbeat_loop())

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            seq = msg.get("seq", 0)

            if msg_type == "ping":
                await ws_manager.send_json(cid, {"type": "pong", "seq": seq})
            elif msg_type == "pong":
                client.last_heartbeat = time.time()
            elif msg_type == "subscribe":
                channels = msg.get("channels", [])
                client.channels = set(channels)
                logger.debug(f"WS client {cid} subscribed to: {client.channels}")
            else:
                await ws_manager.send_json(cid, {
                    "type": "error", "seq": seq,
                    "code": "UNKNOWN_TYPE", "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS client {cid} error: {e}")
    finally:
        if ping_task:
            ping_task.cancel()
        ws_manager.remove(cid)


# ── SSE Events Endpoint ────────────────────────────────────────────────────────


@app.get("/api/events")
async def sse_events(request: Request):
    """Server-Sent Events stream delivering status_update payloads."""

    async def event_stream():
        while True:
            if await request.is_disconnected():
                break
            payload = await _build_status_payload()
            seq = await _next_ws_seq()
            packet = {
                "type": "status_update",
                "seq": seq,
                "payload": payload,
                "ts": time.time(),
            }
            yield f"data: {json.dumps(packet)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# -------- Legacy Redirects: /api/* -> /api/v1/* --------
# NOTE: This catch-all must be registered AFTER all other route definitions so that
# specific /api/v1/* and directly registered routes take precedence over the legacy redirect.
LEGACY_REDIRECT_MAP = {
    "/api/auth/login": "/api/v1/auth/login",
    "/api/auth/refresh": "/api/v1/auth/refresh",
    "/api/contacts": "/api/v1/contacts",
    "/api/rag/search": "/api/v1/rag/search",
    "/api/settings": "/api/v1/settings",
}


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
)
async def legacy_redirect(request: Request, path: str):
    # path = "v1/..." for already-versioned URLs — those should never reach here
    # because the specific router routes are registered first, but guard anyway.
    if path.startswith("v1/"):
        logger.debug(f"Ignoring legacy redirect for already-versioned path: /api/{path}")
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    full_path = f"/api/{path}"
    new_path = LEGACY_REDIRECT_MAP.get(full_path)
    if new_path is None and full_path.startswith("/api/contacts/"):
        new_path = full_path.replace("/api/contacts/", "/api/v1/contacts/", 1)
    elif new_path is None and full_path.startswith("/api/rag/"):
        new_path = full_path.replace("/api/rag/", "/api/v1/rag/", 1)
    elif new_path is None and full_path.startswith("/api/reports/"):
        new_path = full_path.replace("/api/reports/", "/api/v1/reports/", 1)
    elif new_path is None:
        new_path = f"{API_PREFIX}/{path}"

    query = str(request.url.query)
    query_string = f"?{query}" if query else ""
    logger.debug(f"Redirecting {request.method} {full_path} -> {new_path}")
    return RedirectResponse(url=f"{new_path}{query_string}", status_code=307)


# -------- Background status broadcaster (WS protocol v1) --------
async def system_status_broadcaster():
    logger.info("Starting background system status broadcaster (WS v1)...")

    while True:
        try:
            if ws_manager.clients:
                payload = await _build_status_payload()
                seq = await _next_ws_seq()
                packet = {
                    "type": "status_update",
                    "seq": seq,
                    "payload": payload,
                    "ts": time.time(),
                }
                await ws_manager.broadcast("status", packet)
        except Exception as e:
            logger.error(f"Error in status broadcaster loop: {e}")

        await asyncio.sleep(2.0)


if __name__ == "__main__":
    config.validate()
    logger.info("Starting FastAPI Server...")
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=False)
