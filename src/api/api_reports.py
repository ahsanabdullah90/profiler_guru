import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from src.utils.config import config
from src.utils.logger import logger
from src.engine.report_generator import report_generator
from src.engine.settings_manager import settings_manager
from src.api.api_dependencies import get_current_user
from src.utils.validation import validate_safe_param

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])

class GenerateReportRequest(BaseModel):
    start_month: str
    end_month: str
    profile_text: str

@router.post("/contacts/{name}/generate")
def generate_report(name: str, req: GenerateReportRequest, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    try:
        export_dir = Path(config.EXPORTS_DIR)
        os.makedirs(export_dir, exist_ok=True)
        
        pdf_filename = f"{name}_personality_report.pdf"
        pdf_path = export_dir / pdf_filename
        
        # Compile PDF using the existing report_generator singleton
        report_generator.create_assessment_pdf(
            contact=name,
            start_month=req.start_month,
            end_month=req.end_month,
            content=req.profile_text,
            settings=settings_manager.settings,
            out_path=pdf_path
        )
        
        if not pdf_path.exists():
            raise HTTPException(status_code=500, detail="Failed to compile PDF report file")
            
        return {"filename": pdf_filename}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error compiling PDF report for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
