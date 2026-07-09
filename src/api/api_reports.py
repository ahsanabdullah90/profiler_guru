import json
import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.api.api_dependencies import get_current_user
from src.engine.report_generator import report_generator
from src.engine.settings_manager import settings_manager
from src.utils.config import config
from src.utils.logger import logger
from src.utils.task_tracker import task_tracker
from src.utils.validation import validate_safe_param

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])

class GenerateReportRequest(BaseModel):
    start_month: str
    end_month: str
    profile_text: str


def _generate_pdf_async(name: str, start_month: str, end_month: str, profile_text: str):
    """Executes Matplotlib + ReportLab PDF generation in a background thread."""
    task_id = f"pdf_report_{name}"
    try:
        export_dir = Path(config.EXPORTS_DIR)
        os.makedirs(export_dir, exist_ok=True)
        pdf_path = export_dir / f"{name}_personality_report.pdf"

        task_tracker.update_task(task_id, current=25, total=100, status="running")

        # Read assessment metadata for scores / framework / classification
        meta_path = Path(config.CHATS_DIR) / name / "personality_assessment.json"
        scores: dict | None = None
        framework_id: str | None = None
        classification: str | None = None
        try:
            if meta_path.exists():
                with open(meta_path, encoding="utf-8") as f:
                    meta_data = json.load(f)
                scores = meta_data.get("scores")
                framework_id = meta_data.get("framework_id")
                classification = meta_data.get("classification")
        except Exception as e:
            logger.warning(f"Could not read assessment metadata for PDF: {e}")

        # Execute CPU-intensive compilation
        report_generator.create_assessment_pdf(
            contact=name,
            start_month=start_month,
            end_month=end_month,
            content=profile_text,
            settings=settings_manager.settings,
            out_path=pdf_path,
            scores=scores,
            framework_id=framework_id,
            classification=classification,
        )

        task_tracker.complete_task(task_id)
        logger.info(f"Background PDF generation completed for {name}")
    except Exception as e:
        task_tracker.fail_task(task_id, str(e))
        logger.error(f"Error compiling PDF report for {name} in background: {e}")


@router.post("/contacts/{name}/generate")
async def generate_report(
    name: str,
    req: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Schedules a background PDF compilation for the given contact.

    Accepts the already-generated profile text (from /rag/contacts/{name}/profile)
    and the month range used to generate it. Returns immediately with a task ID;
    the actual PDF generation happens in a background thread. Poll
    /contacts/{name}/generate/status to check progress.

    Args:
        name: Contact name (validated against path-traversal regex).
        req: start_month, end_month, and the full profile_text to embed in the PDF.

    Returns:
        {"status": "generating", "filename": "..."}
    """
    validate_safe_param(name, "contact")
    pdf_filename = f"{name}_personality_report.pdf"
    task_id = f"pdf_report_{name}"

    # Register the task persistently in the tracker
    task_tracker.register_task(task_id, f"PDF Report Generation for {name}", total=100)

    # Delegate the synchronous heavy work to a background thread
    background_tasks.add_task(
        _generate_pdf_async,
        name,
        req.start_month,
        req.end_month,
        req.profile_text
    )

    return {"status": "generating", "filename": pdf_filename}


@router.get("/contacts/{name}/generate/status")
def get_generation_status(name: str, current_user: dict = Depends(get_current_user)):
    """Polls the background PDF generation progress.

    Checks both the in-memory task tracker for generation status
    and the file system for the output PDF. Returns one of:
        - {"status": "completed", "filename": "..."}
        - {"status": "generating", "filename": "..."}
        - {"status": "failed", "error": "..."}
        - {"status": "not_started"}

    Args:
        name: Contact name.

    Returns:
        Status dict with current generation state.
    """
    validate_safe_param(name, "contact")
    pdf_filename = f"{name}_personality_report.pdf"
    pdf_path = Path(config.EXPORTS_DIR) / pdf_filename

    task_id = f"pdf_report_{name}"
    active_tasks = task_tracker.get_active_tasks()

    task_status = "not_started"
    error = None

    for task in active_tasks:
        if task.get("id") == task_id:
            task_status = task.get("status")
            error = task.get("error")
            break

    # Check physical file existence and task completion
    if pdf_path.exists() and task_status != "running":
        return {"status": "completed", "filename": pdf_filename}

    if task_status == "failed":
        return {"status": "failed", "error": error}

    if task_status == "running":
        return {"status": "generating", "filename": pdf_filename}

    return {"status": "not_started"}


@router.get("/contacts/{name}/download")
def download_report(name: str, current_user: dict = Depends(get_current_user)):
    """Downloads the compiled personality report PDF for the given contact.

    The PDF must have been compiled first via POST /contacts/{name}/generate.
    Returns a 404 if no PDF exists yet.

    Args:
        name: Contact name.

    Returns:
        FileResponse streaming the PDF with Content-Disposition: attachment.
    """
    validate_safe_param(name, "contact")
    pdf_filename = f"{name}_personality_report.pdf"
    pdf_path = Path(config.EXPORTS_DIR) / pdf_filename

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Personality report PDF has not been compiled yet. Please compile it first.")

    return FileResponse(
        path=str(pdf_path),
        filename=pdf_filename,
        media_type="application/pdf"
    )

