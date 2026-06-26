import os
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from src.utils.config import config
from src.utils.logger import logger
from src.engine.report_generator import report_generator
from src.engine.settings_manager import settings_manager
from src.api.api_dependencies import get_current_user
from src.utils.validation import validate_safe_param
from src.utils.task_tracker import task_tracker

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
        
        # Execute CPU-intensive compilation
        report_generator.create_assessment_pdf(
            contact=name,
            start_month=start_month,
            end_month=end_month,
            content=profile_text,
            settings=settings_manager.settings,
            out_path=pdf_path
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
    """Checks the background PDF generation progress and status."""
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

