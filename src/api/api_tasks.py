import threading
from fastapi import APIRouter, HTTPException, Depends
from typing import Any
from src.utils.logger import logger
from src.utils.task_tracker import task_tracker
from src.api.api_dependencies import get_current_user

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.get("")
def list_tasks(current_user: dict = Depends(get_current_user)):
    """Return all active and recently completed/failed tasks."""
    tasks = task_tracker.get_active_tasks()
    return {"tasks": tasks}


@router.delete("/{task_id}")
def cancel_task(task_id: str, current_user: dict = Depends(get_current_user)):
    """Request cancellation of a running task."""
    tasks = task_tracker.get_active_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in ("running", "cancelling"):
        raise HTTPException(status_code=400, detail="Task is not running")
    task_tracker.request_cancel(task_id)
    return {"status": "cancelling", "task_id": task_id}


@router.post("/vacuum")
def submit_vacuum(current_user: dict = Depends(get_current_user)):
    """Submit a vacuum orphaned vectors task."""
    task_id = "vacuum_orphans"
    existing = task_tracker.get_active_tasks()
    if any(t["id"] == task_id and t["status"] == "running" for t in existing):
        raise HTTPException(status_code=409, detail="Vacuum task already running")

    def _run():
        try:
            from src.engine.rag_engine import rag_engine
            logger.info("Manual vacuum task started")
            deleted = rag_engine.vacuum_orphaned_vectors()
            task_tracker.complete_task(task_id)
            logger.info(f"Manual vacuum completed. Deleted {deleted} orphaned vectors.")
        except Exception as e:
            task_tracker.fail_task(task_id, str(e))
            logger.error(f"Manual vacuum failed: {e}")

    task_tracker.register_task(task_id, "Vacuum Orphaned Vectors")
    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id, "status": "submitted"}


@router.post("/analytics")
def submit_precompute_analytics(current_user: dict = Depends(get_current_user)):
    """Pre-compute and cache analytics for all contacts."""
    task_id = "precompute_analytics"
    existing = task_tracker.get_active_tasks()
    if any(t["id"] == task_id and t["status"] == "running" for t in existing):
        raise HTTPException(status_code=409, detail="Analytics pre-computation already running")

    def _run():
        try:
            from src.services.contacts_service import build_contacts_list, get_contact_analytics
            from src.utils.redis_client import cache_set
            contacts = build_contacts_list()
            if not contacts:
                task_tracker.complete_task(task_id)
                return
            total = len(contacts)
            task_tracker.register_task(task_id, "Precompute Analytics", total=total)
            logger.info(f"Pre-computing analytics for {total} contacts")
            for i, contact in enumerate(contacts):
                if task_tracker.is_cancelled(task_id):
                    logger.info("Analytics pre-computation cancelled")
                    break
                name = contact["name"]
                cache_key = f"analytics:{name}"
                existing = __import__("src.utils.redis_client", fromlist=["cache_get"]).cache_get(cache_key)
                if existing is not None:
                    task_tracker.update_task(task_id, i + 1)
                    continue
                try:
                    result = get_contact_analytics(name)
                    cache_set(cache_key, result, ttl=600)
                except Exception as e:
                    logger.error(f"Failed to precompute analytics for {name}: {e}")
                task_tracker.update_task(task_id, i + 1)
            task_tracker.complete_task(task_id)
            logger.info("Analytics pre-computation completed")
        except Exception as e:
            task_tracker.fail_task(task_id, str(e))
            logger.error(f"Analytics pre-computation failed: {e}")

    task_tracker.register_task(task_id, "Precompute Analytics", total=0)
    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id, "status": "submitted"}


@router.post("/reindex")
def submit_reindex_rag(current_user: dict = Depends(get_current_user)):
    """Re-index RAG vectors for all contacts from markdown files."""
    task_id = "reindex_rag"
    existing = task_tracker.get_active_tasks()
    if any(t["id"] == task_id and t["status"] == "running" for t in existing):
        raise HTTPException(status_code=409, detail="RAG re-index already running")

    def _run():
        try:
            import os
            from src.utils.config import config
            from src.engine.rag_engine import rag_engine
            chats_root = config.CHATS_DIR
            if not os.path.exists(chats_root):
                task_tracker.complete_task(task_id)
                return
            contacts = [d for d in os.listdir(chats_root) if os.path.isdir(os.path.join(chats_root, d))]
            total = len(contacts)
            task_tracker.register_task(task_id, "Reindex RAG Vectors", total=total)
            logger.info(f"Re-indexing RAG for {total} contacts")
            for i, contact in enumerate(contacts):
                if task_tracker.is_cancelled(task_id):
                    logger.info("RAG re-index cancelled")
                    break
                chats_dir = os.path.join(chats_root, contact, "Chats")
                if not os.path.isdir(chats_dir):
                    task_tracker.update_task(task_id, i + 1)
                    continue
                batch_data = []
                for fname in os.listdir(chats_dir):
                    if not fname.endswith(".md"):
                        continue
                    month = fname[:-3]
                    fpath = os.path.join(chats_dir, fname)
                    try:
                        with open(fpath, encoding="utf-8") as f:
                            content = f.read()
                        if content.strip():
                            batch_data.append((contact, month, content))
                    except Exception as e:
                        logger.error(f"Failed reading {fpath}: {e}")
                if batch_data:
                    try:
                        rag_engine.add_messages_batch(batch_data)
                    except Exception as e:
                        logger.error(f"Failed indexing {contact}: {e}")
                task_tracker.update_task(task_id, i + 1)
            task_tracker.complete_task(task_id)
            logger.info("RAG re-index completed")
        except Exception as e:
            task_tracker.fail_task(task_id, str(e))
            logger.error(f"RAG re-index failed: {e}")

    task_tracker.register_task(task_id, "Reindex RAG Vectors", total=0)
    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id, "status": "submitted"}
