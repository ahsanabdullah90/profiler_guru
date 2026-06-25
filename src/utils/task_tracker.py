# src/utils/task_tracker.py
"""A thread-safe global background task tracker.
Enables communication of progress, status, and cancel requests between background threads and Streamlit.
"""
import threading
import time
from typing import Dict, List, Any

class TaskTracker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TaskTracker, cls).__new__(cls)
                cls._instance._tasks = {}
                cls._instance._cancel_events = {}
            return cls._instance

    def register_task(self, task_id: str, name: str, total: int = 0) -> str:
        """Register a new background task."""
        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "name": name,
                "current": 0,
                "total": total,
                "status": "running",
                "start_time": time.time(),
                "error": None
            }
            self._cancel_events[task_id] = threading.Event()
        return task_id

    def update_task(self, task_id: str, current: int, total: int = None, status: str = "running"):
        """Update progress of a registered task."""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["current"] = current
                if total is not None:
                    self._tasks[task_id]["total"] = total
                self._tasks[task_id]["status"] = status

    def complete_task(self, task_id: str):
        """Mark task as successfully completed."""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = "completed"
                # Keep it in history briefly, then cleanup
                self._tasks[task_id]["current"] = self._tasks[task_id]["total"]

    def fail_task(self, task_id: str, error_msg: str):
        """Mark task as failed with an error message."""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = "failed"
                self._tasks[task_id]["error"] = error_msg

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Return a list of all active or recently updated tasks."""
        with self._lock:
            # Filter and return running, completed, or failed tasks
            active = []
            now = time.time()
            for tid, t in list(self._tasks.items()):
                # Keep completed or failed tasks in the UI for 10 seconds, then prune
                if t["status"] in ["completed", "failed"]:
                    if now - t["start_time"] > 300: # Keep longer for better visibility, e.g. 5 minutes
                        del self._tasks[tid]
                        if tid in self._cancel_events:
                            del self._cancel_events[tid]
                        continue
                active.append(t)
            return active

    def request_cancel(self, task_id: str):
        """Request cancellation of a running task."""
        with self._lock:
            if task_id in self._cancel_events:
                self._cancel_events[task_id].set()
                if task_id in self._tasks:
                    self._tasks[task_id]["status"] = "cancelling"

    def is_cancelled(self, task_id: str) -> bool:
        """Check if cancellation has been requested for this task."""
        with self._lock:
            event = self._cancel_events.get(task_id)
            return event.is_set() if event else False

from src.utils.lazy_proxy import LazyProxy

task_tracker = LazyProxy(TaskTracker)
