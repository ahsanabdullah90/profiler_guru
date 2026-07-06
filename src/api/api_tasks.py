import threading

from fastapi import APIRouter, Depends, HTTPException
from src.api.api_dependencies import get_current_user
from src.utils.logger import logger
from src.utils.task_tracker import task_tracker

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
            from src.utils.redis_client import cache_get, cache_set
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
                existing = cache_get(cache_key)
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


def start_reindex_rag_task():
    """Launches the RAG reindex task in a background thread with persistent state."""
    task_id = "reindex_rag"
    MAX_RETRIES = 5
    existing = task_tracker.get_active_tasks()
    if any(t["id"] == task_id and t["status"] == "running" for t in existing):
        return {"task_id": task_id, "status": "already_running"}

    def _run():
        try:
            import time
            import os
            from src.engine.rag_engine import rag_engine
            from src.engine.metrics_engine import MetricsEngine
            from src.utils.config import config

            me = MetricsEngine()
            chats_root = config.CHATS_DIR

            # Check for incomplete reindex (resume) or start new batch
            pending = me.get_pending_reindex_contacts()
            if pending:
                contacts = pending
                logger.info(f"Resuming RAG reindex: {len(contacts)} contacts remaining")
            else:
                if not os.path.exists(chats_root):
                    task_tracker.complete_task(task_id)
                    return
                contacts = [d for d in os.listdir(chats_root) if os.path.isdir(os.path.join(chats_root, d))]
                me.init_reindex_batch(contacts)
                logger.info(f"Starting new RAG reindex: {len(contacts)} contacts")

            total = me.get_reindex_total_contacts()
            completed_before = total - len(contacts)
            task_tracker.register_task(task_id, "Reindex RAG Vectors", total=total)
            if completed_before > 0:
                task_tracker.update_task(task_id, completed_before)

            # Warm up Ollama
            logger.info("Warming up Ollama embedding model...")
            try:
                rag_engine.embedding_function(["warmup"])
                logger.info("Ollama model warmed up successfully.")
            except Exception as e:
                logger.warning(f"Ollama warmup failed: {e}")
                time.sleep(10)

            for i, contact in enumerate(contacts):
                if task_tracker.is_cancelled(task_id):
                    logger.info("RAG re-index cancelled")
                    break

                # Skip contacts that already exceeded max retries
                retry_count = me.get_reindex_retry_count(contact)
                if retry_count >= MAX_RETRIES:
                    logger.warning(f"Skipping {contact}: max retries ({MAX_RETRIES}) exceeded")
                    task_tracker.update_task(task_id, completed_before + i + 1)
                    continue

                me.mark_contact_status(contact, "indexing")
                chats_dir = os.path.join(chats_root, contact, "Chats")

                if not os.path.isdir(chats_dir):
                    me.mark_contact_status(contact, "completed")
                    task_tracker.update_task(task_id, completed_before + i + 1)
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
                        me.mark_contact_status(contact, "completed")
                    except Exception as e:
                        new_count = me.increment_reindex_retry(contact)
                        if new_count >= MAX_RETRIES:
                            me.mark_contact_status(contact, "failed", error_msg=str(e))
                            logger.error(f"Failed indexing {contact} after {MAX_RETRIES} retries: {e}")
                        else:
                            me.mark_contact_status(contact, "pending")
                            logger.warning(f"Failed indexing {contact} (attempt {new_count}/{MAX_RETRIES}): {e}. Will retry.")
                else:
                    me.mark_contact_status(contact, "completed")

                task_tracker.update_task(task_id, completed_before + i + 1)
                time.sleep(0.5)

            task_tracker.complete_task(task_id)
            rag_engine.recreated = False

            # Remove sentinel file
            sentinel = config.DATA_DIR / "chroma_db" / ".reindex_pending"
            try:
                if sentinel.exists():
                    sentinel.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove reindex sentinel: {e}")

            # Log failed contacts
            cur = me.conn.cursor()
            cur.execute("SELECT chat_name, error_msg, retry_count FROM reindex_state WHERE status = 'failed';")
            failed = cur.fetchall()
            if failed:
                logger.warning(f"Reindex completed with {len(failed)} permanently failed contacts:")
                for name, err, retries in failed:
                    logger.warning(f"  - {name} ({retries} retries): {err}")

            me.clear_reindex_state()
            logger.info("RAG re-index completed")
        except Exception as e:
            task_tracker.fail_task(task_id, str(e))
            logger.error(f"RAG re-index failed: {e}")

    task_tracker.register_task(task_id, "Reindex RAG Vectors", total=0)
    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id, "status": "submitted"}


@router.post("/reindex")
def submit_reindex_rag(current_user: dict = Depends(get_current_user)):
    """Re-index RAG vectors for all contacts from markdown files."""
    result = start_reindex_rag_task()
    if result.get("status") == "already_running":
        raise HTTPException(status_code=409, detail="RAG re-index already running")
    return result
