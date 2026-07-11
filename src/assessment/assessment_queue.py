import json
import os
import queue
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from src.utils.logger import logger
from src.utils.task_tracker import task_tracker


class CancelledError(Exception):
    pass


_ERROR_PROFILE_PATTERNS = [
    "Error:",
    "is not reachable",
    "failed to generate",
    "HTTP Error",
    "Ollama generation failed",
    "Traceback (most recent call last)",
]


def _is_cloud_model_name(model_name: str) -> bool:
    import re
    return bool(re.search(
        r"^(gemini|gpt|claude|o1-|o3-)", model_name, re.IGNORECASE
    ))


def _is_error_profile(profile_text: str | None) -> bool:
    if not profile_text:
        return False
    return any(p in profile_text for p in _ERROR_PROFILE_PATTERNS)

MAX_QUEUE_DEPTH = 10


class QueueFull(Exception):
    pass


class AssessmentJob:
    __slots__ = (
        "job_id", "contact_name", "framework_id",
        "start_month", "end_month", "model_provider", "model_name",
        "user_consent", "status", "progress", "progress_message",
        "queue_position", "created_at", "started_at", "completed_at",
        "error_message", "result_profile", "result_meta",
    )

    def __init__(self, job_id: str, contact_name: str, framework_id: str,
                 start_month: str, end_month: str,
                 model_provider: str | None, model_name: str | None,
                 user_consent: bool):
        self.job_id = job_id
        self.contact_name = contact_name
        self.framework_id = framework_id
        self.start_month = start_month
        self.end_month = end_month
        self.model_provider = model_provider
        self.model_name = model_name
        self.user_consent = user_consent
        self.status = "queued"
        self.progress = 0
        self.progress_message = "Queued — waiting for worker…"
        self.queue_position = 0
        self.created_at = time.time()
        self.started_at: float | None = None
        self.completed_at: float | None = None
        self.error_message: str | None = None
        self.result_profile: str | None = None
        self.result_meta: dict | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "contact_name": self.contact_name,
            "framework_id": self.framework_id,
            "start_month": self.start_month,
            "end_month": self.end_month,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "user_consent": self.user_consent,
            "status": self.status,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "queue_position": self.queue_position,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
        }


class AssessmentQueue:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self._jobs: dict[str, AssessmentJob] = {}
        self._job_lock = threading.Lock()
        self._queue: "queue.Queue[str | None]" = queue.Queue()
        self._cancel_events: dict[str, threading.Event] = {}
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Assessment queue background worker thread started.")

    def enqueue(self, contact_name: str, framework_id: str,
                start_month: str, end_month: str,
                model_provider: str | None = None,
                model_name: str | None = None,
                user_consent: bool = False) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = AssessmentJob(job_id, contact_name, framework_id,
                            start_month, end_month,
                            model_provider, model_name, user_consent)

        with self._job_lock:
            queued_count = sum(1 for j in self._jobs.values() if j.status == "queued")
            if queued_count >= MAX_QUEUE_DEPTH:
                raise QueueFull(
                    f"Assessment queue is full ({MAX_QUEUE_DEPTH} queued). "
                    "Please wait for a running job to complete."
                )
            self._jobs[job_id] = job
            self._refresh_positions()
            job.queue_position = queued_count + 1

        self._queue.put(job_id)
        logger.info(f"Enqueued assessment job {job_id} for contact '{contact_name}'")
        return job_id

    def get_job(self, job_id: str) -> dict | None:
        with self._job_lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None

    def get_contact_job(self, contact_name: str) -> dict | None:
        with self._job_lock:
            candidates = [j for j in self._jobs.values()
                          if j.contact_name == contact_name
                          and j.status in ("queued", "running", "completed")]
            if not candidates:
                return None
            latest = max(candidates, key=lambda j: j.created_at)
            return latest.to_dict()

    def get_all_jobs(self) -> list[dict]:
        with self._job_lock:
            return sorted(
                [j.to_dict() for j in self._jobs.values()],
                key=lambda d: d["created_at"],
                reverse=True,
            )

    def cancel_job(self, job_id: str) -> bool:
        with self._job_lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status == "queued":
                job.status = "cancelled"
                job.progress_message = "Cancelled by user"
                job.completed_at = time.time()
                self._refresh_positions()
                self._prune_cancel_events(job_id)
                logger.info(f"Cancelled queued assessment job {job_id}")
                return True
            if job.status == "running":
                job.status = "cancelling"
                job.progress_message = "Cancelling…"
                event = self._cancel_events.get(job_id)
                if event:
                    event.set()
                logger.info(f"Requested cancellation of running assessment job {job_id}")
                return True
            return False

    def _worker_loop(self):
        while True:
            job_id = self._queue.get()
            if job_id is None:
                break

            with self._job_lock:
                job = self._jobs.get(job_id)
                if job is None or job.status == "cancelled":
                    self._queue.task_done()
                    continue

            self._run_job(job)
            self._queue.task_done()

    def _run_job(self, job: AssessmentJob):
        job.started_at = time.time()
        job.status = "running"
        job.progress = 0
        job.progress_message = "Starting assessment…"
        self._refresh_positions()

        task_tracker.register_task(
            job.job_id,
            f"Assessment: {job.contact_name}",
            total=100,
            task_type="assessment",
            extra={"contact": job.contact_name},
        )
        task_tracker.update_task(job.job_id, 0)

        cancel_event = threading.Event()
        self._cancel_events[job.job_id] = cancel_event

        def progress_callback(percent: int, message: str):
            if cancel_event.is_set():
                return
            with self._job_lock:
                job.progress = min(percent, 100)
                job.progress_message = message
            task_tracker.update_task(job.job_id, job.progress, extra={"message": message})

        try:
            from src.engine.rag_engine import rag_engine
            from src.utils.config import config
            from src.utils.markdown import parse_message_blocks

            # 1. Fetch markdown snippets
            if cancel_event.is_set(): raise CancelledError()
            progress_callback(10, "Fetching chat logs…")
            markdown_snippets = rag_engine.fetch_markdown_snippets(
                job.contact_name, job.start_month, job.end_month
            )
            if not markdown_snippets:
                raise ValueError("No message snippets found in the selected date range.")
            raw_blocks = parse_message_blocks(markdown_snippets)
            total_messages = len(raw_blocks)
            if total_messages < getattr(config, "ASSESSMENT_MIN_BLOCKS", 5):
                raise ValueError(
                    f"Chat history density is insufficient. Selected range has {total_messages} message blocks, "
                    f"but a minimum of {getattr(config, 'ASSESSMENT_MIN_BLOCKS', 5)} is required."
                )

            token_estimate = rag_engine.estimate_token_count(markdown_snippets)

            # 3. Token budget
            if cancel_event.is_set(): raise CancelledError()
            progress_callback(35, "Building assessment prompt…")
            use_explicit_model = bool(job.model_provider and job.model_name)
            if use_explicit_model:
                is_cloud = _is_cloud_model_name(job.model_name)
                cloud_available = is_cloud and job.user_consent and config.ENABLE_CLOUD_AI
            else:
                will_use_cloud = token_estimate > getattr(config, "PERSONA_ASSESS_MAX_LOCAL_TOKENS", 15000)
                cloud_available = will_use_cloud and job.user_consent and config.ENABLE_CLOUD_AI
            max_chars = getattr(config, "RAG_TOKEN_BUDGET_GEMINI", 300000) if cloud_available else getattr(config, "RAG_TOKEN_BUDGET_OLLAMA", 15000)
            truncated = False
            if len(markdown_snippets) > max_chars:
                markdown_snippets = markdown_snippets[:max_chars] + "\n\n[Conversation truncated for token limits…]"
                truncated = True

            # 4. Run assessment
            if cancel_event.is_set(): raise CancelledError()
            from src.assessment.pipeline import run_assessment

            result = run_assessment(
                name=job.contact_name,
                framework_id=job.framework_id,
                markdown_snippets=markdown_snippets,
                total_messages=total_messages,
                avg_sentiment=0.0,
                token_estimate=token_estimate,
                start_month=job.start_month,
                end_month=job.end_month,
                model_provider=job.model_provider,
                model_name=job.model_name,
                user_consent=job.user_consent,
                progress_callback=progress_callback,
            )

            if cancel_event.is_set(): raise CancelledError()

            # 5. Validate output
            profile_text = result["profile_text"]
            if profile_text and _is_error_profile(profile_text):
                raise ValueError("The assessment generation failed. Please check your model configuration and try again.")

            # 6. Save to disk
            progress_callback(92, "Saving assessment to disk…")
            contact_dir = Path(config.CHATS_DIR) / job.contact_name
            assessments_dir = contact_dir / "assessments"
            os.makedirs(assessments_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            fw_id = job.framework_id or "unknown"
            versioned_stem = f"{fw_id}_{timestamp}"

            from src.assessment.frameworks import get_framework_hash
            meta_data = {
                "start_month": job.start_month,
                "end_month": job.end_month,
                "provider": job.model_provider or "ollama",
                "model": job.model_name or "default",
                "generated_at": datetime.now().isoformat(),
                "citations": result.get("citations", []),
                "truncated": truncated,
                "model_provider": job.model_provider,
                "model_name": job.model_name,
                "framework_id": job.framework_id,
                "scores": result.get("scores"),
                "classification": result.get("classification"),
                "pipeline_mode": result.get("pipeline_mode", "single"),
                "total_steps": result.get("total_steps", 1),
                "versioned_file": f"{versioned_stem}.md",
                "framework_version": get_framework_hash(job.framework_id),
            }

            v_profile = assessments_dir / f"{versioned_stem}.md"
            v_meta = assessments_dir / f"{versioned_stem}.json"
            with open(v_profile, "w", encoding="utf-8") as f:
                f.write(profile_text)
            with open(v_meta, "w", encoding="utf-8") as f:
                json.dump(meta_data, f, indent=2)

            latest_profile = contact_dir / "personality_assessment.md"
            latest_meta = contact_dir / "personality_assessment.json"
            tmp_profile = contact_dir / "personality_assessment.md.tmp"
            with open(tmp_profile, "w", encoding="utf-8") as f:
                f.write(profile_text)
            os.replace(tmp_profile, latest_profile)
            tmp_meta = contact_dir / "personality_assessment.json.tmp"
            with open(tmp_meta, "w", encoding="utf-8") as f:
                json.dump(meta_data, f, indent=2)
            os.replace(tmp_meta, latest_meta)

            from src.engine.metrics_engine import MetricsEngine
            _me = MetricsEngine()
            _me.save_assessment_metadata(
                contact_name=job.contact_name, meta=meta_data, file_path=str(v_profile)
            )

            if cancel_event.is_set(): raise CancelledError()
            progress_callback(100, "Assessment complete")

            with self._job_lock:
                job.status = "completed"
                job.progress = 100
                job.progress_message = "Assessment complete"
                job.completed_at = time.time()
                job.result_profile = profile_text
                job.result_meta = meta_data
            task_tracker.complete_task(job.job_id)
            logger.info(f"Assessment job {job.job_id} completed for {job.contact_name}")

        except CancelledError:
            with self._job_lock:
                job.status = "cancelled"
                job.progress_message = "Cancelled by user"
                job.completed_at = time.time()
            task_tracker.fail_task(job.job_id, "Cancelled by user")
            logger.info(f"Assessment job {job.job_id} cancelled mid-run")
        except Exception as e:
            with self._job_lock:
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = time.time()
                job.progress_message = f"Failed: {e}"
            task_tracker.fail_task(job.job_id, str(e))
            logger.error(f"Assessment job {job.job_id} failed: {e}")
        finally:
            self._prune_cancel_events(job.job_id)

    def _refresh_positions(self):
        queued = sorted(
            [j for j in self._jobs.values() if j.status == "queued"],
            key=lambda j: j.created_at,
        )
        for idx, j in enumerate(queued, start=1):
            j.queue_position = idx

    def _prune_cancel_events(self, job_id: str):
        self._cancel_events.pop(job_id, None)


assessment_queue = AssessmentQueue()
