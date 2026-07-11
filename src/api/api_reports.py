import json
import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.api.api_dependencies import get_current_user, resolve_contact
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


def _generate_pdf_async(chat_name: str, start_month: str, end_month: str, profile_text: str):
    """Executes Matplotlib + ReportLab PDF generation in a background thread."""
    task_id = f"pdf_report_{chat_name}"
    try:
        export_dir = Path(config.EXPORTS_DIR)
        os.makedirs(export_dir, exist_ok=True)
        pdf_path = export_dir / f"{chat_name}_personality_report.pdf"

        task_tracker.update_task(task_id, current=25, total=100, status="running")

        # Read assessment metadata for scores / framework / classification
        meta_path = Path(config.CHATS_DIR) / chat_name / "personality_assessment.json"
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
            contact=chat_name,
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
        logger.info(f"Background PDF generation completed for {chat_name}")
    except Exception as e:
        task_tracker.fail_task(task_id, str(e))
        logger.error(f"Error compiling PDF report for {chat_name} in background: {e}")


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
        name: Contact name or UUID.
        req: start_month, end_month, and the full profile_text to embed in the PDF.

    Returns:
        {"status": "generating", "filename": "..."}
    """
    validate_safe_param(name, "contact")
    _, chat_name = resolve_contact(name)
    if chat_name is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    pdf_filename = f"{chat_name}_personality_report.pdf"
    task_id = f"pdf_report_{chat_name}"

    # Register the task persistently in the tracker
    task_tracker.register_task(task_id, f"PDF Report Generation for {chat_name}", total=100)

    # Delegate the synchronous heavy work to a background thread
    background_tasks.add_task(
        _generate_pdf_async,
        chat_name,
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
        name: Contact name or UUID.

    Returns:
        Status dict with current generation state.
    """
    validate_safe_param(name, "contact")
    _, chat_name = resolve_contact(name)
    if chat_name is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    pdf_filename = f"{chat_name}_personality_report.pdf"
    pdf_path = Path(config.EXPORTS_DIR) / pdf_filename

    task_id = f"pdf_report_{chat_name}"
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
        name: Contact name or UUID.

    Returns:
        FileResponse streaming the PDF with Content-Disposition: attachment.
    """
    validate_safe_param(name, "contact")
    _, chat_name = resolve_contact(name)
    if chat_name is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    pdf_filename = f"{chat_name}_personality_report.pdf"
    pdf_path = Path(config.EXPORTS_DIR) / pdf_filename

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Personality report PDF has not been compiled yet. Please compile it first.")

    return FileResponse(
        path=str(pdf_path),
        filename=pdf_filename,
        media_type="application/pdf"
    )


@router.get("/contacts/{name}/fhir")
def export_fhir_bundle(name: str, current_user: dict = Depends(get_current_user)):
    """Export patient profile and assessment history as an HL7 FHIR JSON Bundle."""
    validate_safe_param(name, "contact")
    _, chat_name = resolve_contact(name)
    if chat_name is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    from src.engine.metrics_engine import MetricsEngine
    from datetime import datetime
    me = MetricsEngine()

    profile = me.get_client_profile(chat_name)
    if not profile:
        raise HTTPException(status_code=404, detail="Client profile not found")

    # Build Patient resource
    patient_id = profile.get("patient_id") or "unknown"
    patient_resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [
            {
                "system": "https://profile-guru.org/fhir/sid/mrn",
                "value": profile.get("mrn")
            }
        ] if profile.get("mrn") else [],
        "name": [
            {
                "use": "official",
                "text": profile.get("display_name") or chat_name
            }
        ],
        "telecom": [],
        "gender": "unknown",
    }

    if profile.get("email"):
        patient_resource["telecom"].append({
            "system": "email",
            "value": profile["email"],
            "use": "home"
        })
    if profile.get("mobile"):
        patient_resource["telecom"].append({
            "system": "phone",
            "value": profile["mobile"],
            "use": "mobile"
        })
    if profile.get("dob"):
        patient_resource["birthDate"] = profile["dob"]

    # Get assessment history
    history = me.get_assessment_history(chat_name)
    entry_resources = [
        {
            "fullUrl": f"urn:uuid:{patient_id}",
            "resource": patient_resource
        }
    ]

    for idx, item in enumerate(history):
        obs_id = f"obs-{item['history_id']}"
        # Parse scores
        scores = item.get("scores") or {}
        components = []
        for key, val in scores.items():
            components.append({
                "code": {
                    "coding": [
                        {
                            "system": "https://profile-guru.org/fhir/CodeSystem/dimensions",
                            "code": key,
                            "display": key.replace("_", " ").title()
                        }
                    ],
                    "text": key.replace("_", " ").title()
                },
                "valueQuantity": {
                    "value": float(val),
                    "unit": "Score (0-10)",
                    "system": "http://unitsofmeasure.org",
                    "code": "1"
                }
            })

        obs_resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "social-history",
                            "display": "Social History"
                        }
                    ],
                    "text": "Behavioral Assessment"
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "https://profile-guru.org/fhir/CodeSystem/frameworks",
                        "code": item["framework_id"],
                        "display": item["framework_id"].replace("_", " ").title()
                    }
                ],
                "text": f"{item['framework_id'].replace('_', ' ').title()} Assessment"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": item["generated_at"],
            "valueString": item.get("summary") or item.get("classification") or "",
            "component": components,
            "device": {
                "display": f"Profile-Guru RAG Pipeline ({item.get('model_name') or 'Default Model'})"
            }
        }

        # Include framework version if available
        if item.get("framework_version"):
            obs_resource.setdefault("meta", {}).setdefault("tag", []).append({
                "system": "https://profile-guru.org/fhir/sid/framework-version",
                "code": item["framework_version"]
            })

        entry_resources.append({
            "fullUrl": f"urn:uuid:{obs_id}",
            "resource": obs_resource
        })

    bundle = {
        "resourceType": "Bundle",
        "id": f"bundle-export-{chat_name}",
        "type": "collection",
        "meta": {
            "lastUpdated": datetime.now().isoformat() + "Z",
            "tag": [
                {
                    "system": "https://profile-guru.org/fhir/sid/compliance",
                    "code": "fhir_compliance_note",
                    "display": "This Bundle conforms to FHIR R4 structural requirements. SNOMED/LOINC code mappings for custom behavioral dimensions are not included. Clinical staff must review before import into EHR systems."
                }
            ]
        },
        "entry": entry_resources
    }

    return bundle

