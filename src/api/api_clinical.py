"""Clinical questionnaire administration endpoints — PHQ-9, GAD-7, BHS."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from src.api.api_dependencies import get_current_user
from src.assessment.frameworks import get_framework
from src.assessment.scorers import score_questionnaire
from src.engine.metrics_engine import MetricsEngine
from src.utils.logger import logger
from src.utils.validation import validate_safe_param

router = APIRouter(prefix="/api/v1/clinical", tags=["Clinical"])

_me = MetricsEngine()


class QuestionnaireSubmitRequest(BaseModel):
    framework_id: str = Field(..., min_length=3, max_length=32)
    responses: dict[str, int]


@router.post("/{patient_or_contact}/assessments")
def submit_assessment(
    patient_or_contact: str,
    req: QuestionnaireSubmitRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit completed questionnaire responses and receive the scored result.

    The practitioner fills in the questionnaire items and submits.
    Scoring is deterministic (sum + cut-point band). No LLM call.
    """
    validate_safe_param(patient_or_contact, "patient_id")

    # Resolve patient_id
    patient_id = patient_or_contact
    profile = _me.get_patient_by_id(patient_or_contact)
    if profile is None:
        from src.engine.consent_gate import get_patient_id_from_chat_name
        resolved = get_patient_id_from_chat_name(patient_or_contact)
        if resolved:
            patient_id = resolved
        else:
            raise HTTPException(status_code=404, detail=f"Patient not found: {patient_or_contact}")

    # Validate framework exists and is a questionnaire
    fw = get_framework(req.framework_id)
    if not fw:
        raise HTTPException(status_code=400, detail=f"Unknown framework: {req.framework_id}")
    if fw.get("kind") != "questionnaire":
        raise HTTPException(
            status_code=400,
            detail=f"Framework '{req.framework_id}' is not a questionnaire. "
                   f"Use the assessment profile endpoint for trait frameworks.",
        )

    # Score
    try:
        result = score_questionnaire(req.framework_id, req.responses)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Record in assessment_history
    now = datetime.now(UTC).isoformat()
    meta = {
        "framework_id": req.framework_id,
        "generated_at": now,
        "scores": result["responses"],
    }
    _me.save_assessment_metadata(
        contact_name=patient_id,
        meta=meta,
        file_path=None,
    )

    logger.info(
        f"Questionnaire scored: patient={patient_id}, instrument={req.framework_id}, "
        f"total={result['total']}, band={result['band']}"
    )
    return {
        "status": "scored",
        "patient_id": patient_id,
        "result": result,
    }


@router.get("/{patient_or_contact}/assessments/{framework_id}/history")
def get_assessment_history(
    patient_or_contact: str,
    framework_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get all scored assessments for a patient/instrument combination."""
    validate_safe_param(patient_or_contact, "patient_id")

    patient_id = patient_or_contact
    profile = _me.get_patient_by_id(patient_or_contact)
    if profile is None:
        from src.engine.consent_gate import get_patient_id_from_chat_name
        resolved = get_patient_id_from_chat_name(patient_or_contact)
        if resolved:
            patient_id = resolved
        else:
            raise HTTPException(status_code=404, detail=f"Patient not found: {patient_or_contact}")

    all_history = _me.get_assessment_history(patient_id)
    filtered = [h for h in all_history if h.get("framework_id") == framework_id]

    return {"patient_id": patient_id, "framework_id": framework_id, "history": filtered}
