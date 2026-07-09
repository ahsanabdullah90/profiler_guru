"""Clinical questionnaire administration & session audio upload endpoints."""

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from src.api.api_dependencies import get_current_user
from src.assessment.frameworks import get_framework
from src.assessment.scorers import score_questionnaire
from src.engine.media_processor import media_processor
from src.engine.metrics_engine import MetricsEngine
from src.utils.config import config
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


ALLOWED_AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".ogg", ".webm"}


@router.post("/{patient_or_contact}/audio/upload")
async def upload_session_audio(
    patient_or_contact: str,
    file: UploadFile = File(...),
    consent_version: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    """Upload a session audio file for transcription.

    Accepts .m4a, .mp3, .wav, .ogg, .webm files. Saves to the patient's
    audio directory and enqueues for transcription. Returns a session_id
    that can be used to poll transcription status.
    """
    validate_safe_param(patient_or_contact, "patient_id")

    # Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
        )

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

    # Ensure audio directory exists
    audio_dir = Path(config.CHATS_DIR) / patient_or_contact / "Audio"
    os.makedirs(audio_dir, exist_ok=True)

    # Generate unique filename
    stem = f"session_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
    audio_path = audio_dir / f"{stem}{ext}"

    # Save file
    content = await file.read()
    with open(audio_path, "wb") as f:
        f.write(content)

    # Record in session_audio table
    result = _me.save_session_audio(
        contact_name=patient_or_contact,
        audio_path=str(audio_path),
        original_filename=file.filename,
        consent_version=consent_version or None,
    )

    # Enqueue transcription — we use a background thread directly since the
    # existing TranscriptionQueue is tied to IG markdown message format
    def _transcribe_async(session_id: str, audio_path: str):
        try:
            transcript = media_processor.transcribe_audio(str(audio_path))
            if transcript.startswith("Transcription failed"):
                raise Exception(transcript)
            duration = None  # media_processor doesn't expose duration currently
            _me.update_session_transcript(session_id, transcript, duration)
            logger.info(f"Session audio transcribed: session_id={session_id}")
        except Exception as e:
            logger.error(f"Session audio transcription failed: session_id={session_id}, error={e}")
            _me.update_session_transcript(session_id, f"[Transcription failed: {e}]")

    import threading
    thread = threading.Thread(
        target=_transcribe_async,
        args=(result["session_id"], str(audio_path)),
        daemon=True,
    )
    thread.start()

    logger.info(f"Session audio uploaded: patient={patient_id}, session_id={result['session_id']}, file={file.filename}")
    return {
        "status": "uploaded",
        "patient_id": patient_id,
        "session_id": result["session_id"],
        "audio_path": str(audio_path),
        "uploaded_at": result["uploaded_at"],
    }


@router.get("/{patient_or_contact}/audio")
def list_session_audio(
    patient_or_contact: str,
    current_user: dict = Depends(get_current_user),
):
    """List all session audio recordings for a patient."""
    validate_safe_param(patient_or_contact, "patient_id")
    recordings = _me.get_session_audio(patient_or_contact)
    return {"patient_id": patient_or_contact, "recordings": recordings}


@router.delete("/{patient_or_contact}")
def purge_patient(
    patient_or_contact: str,
    reason: str = "Patient request",
    current_user: dict = Depends(get_current_user),
):
    """Right-to-be-forgotten — cascade-delete ALL data for a patient.

    Removes: client profile, consents, clinical notes, assessment history,
    session audio records, chat files, audio files, photos, ChromaDB vectors.
    Writes a tombstone to the purged_patients table.
    """
    validate_safe_param(patient_or_contact, "patient_id")
    logger.warning(f"PURGE requested for patient={patient_or_contact}, reason={reason}")

    result = _me.purge_patient(patient_or_contact)
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=f"Patient not found: {patient_or_contact}")

    logger.warning(f"PURGE completed: patient={patient_or_contact}, records_deleted={result.get('records_deleted', 0)}")
    return result


@router.get("/purged-patients")
def list_purged_patients(current_user: dict = Depends(get_current_user)):
    """List all patients that have been purged (right-to-be-forgotten tombstones)."""
    return {"purged_patients": _me.get_purged_patients()}
