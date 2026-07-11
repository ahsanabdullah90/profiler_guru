"""Consent attestation endpoints — manage patient consent records."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api.api_dependencies import get_current_user, resolve_contact
from src.engine.consent_gate import CONSENT_TYPES, get_patient_id_from_chat_name
from src.engine.metrics_engine import MetricsEngine

_me = MetricsEngine()
from src.utils.logger import logger
from src.utils.validation import validate_safe_param

router = APIRouter(prefix="/api/v1/consent", tags=["Consent"])


class ConsentAttestRequest(BaseModel):
    consent_type: str
    consent_version: str
    notes: str = ""


class ConsentRevokeRequest(BaseModel):
    consent_type: str


@router.post("/{patient_or_contact}/attest")
def attest_consent(
    patient_or_contact: str,
    request: ConsentAttestRequest,
    current_user: dict = Depends(get_current_user),
):
    """Practitioner attests that they have obtained written consent.

    Args:
        patient_or_contact: patient_id or chat_name (IG handle).
        request: ConsentAttestRequest model containing consent_type, consent_version, and optional notes.

    Returns the created consent record.
    """
    validate_safe_param(patient_or_contact, "patient_id")

    consent_type = request.consent_type
    consent_version = request.consent_version
    notes = request.notes

    if consent_type not in CONSENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid consent_type. Must be one of: {', '.join(sorted(CONSENT_TYPES))}",
        )

    # Resolve patient_id from chat_name if needed
    patient_id = patient_or_contact
    profile = _me.get_patient_by_id(patient_or_contact)
    if profile is None:
        # Try resolving as chat_name
        resolved = get_patient_id_from_chat_name(patient_or_contact)
        if resolved:
            patient_id = resolved
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Patient not found: {patient_or_contact}",
            )

    # Revoke any existing active consent of this type first
    _me.revoke_consent(patient_id, consent_type)

    # Create new consent attestation
    result = _me.add_consent_attestation(
        patient_id=patient_id,
        consent_type=consent_type,
        consent_version=consent_version,
        notes=notes,
    )

    # Update denormalized flag
    _me.set_consent_active(patient_id, True)

    logger.info(f"Consent attested: patient={patient_id}, type={consent_type}, version={consent_version}")
    return {"status": "attested", **result}


@router.post("/{patient_or_contact}/revoke")
def revoke_consent(
    patient_or_contact: str,
    request: ConsentRevokeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Revoke all active consent records of the given type for a patient.

    Args:
        patient_or_contact: patient_id or chat_name.
        request: ConsentRevokeRequest model containing consent_type.

    Returns the updated consent status.
    """
    validate_safe_param(patient_or_contact, "patient_id")

    consent_type = request.consent_type

    if consent_type not in CONSENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid consent_type. Must be one of: {', '.join(sorted(CONSENT_TYPES))}",
        )

    patient_id = patient_or_contact
    profile = _me.get_patient_by_id(patient_or_contact)
    if profile is None:
        resolved = get_patient_id_from_chat_name(patient_or_contact)
        if resolved:
            patient_id = resolved
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Patient not found: {patient_or_contact}",
            )

    _me.revoke_consent(patient_id, consent_type)

    logger.info(f"Consent revoked: patient={patient_id}, type={consent_type}")
    return {
        "status": "revoked",
        "patient_id": patient_id,
        "consent_type": consent_type,
        "active_consents": _me.get_active_consents(patient_id),
    }


@router.get("/{patient_or_contact}")
def list_consents(
    patient_or_contact: str,
    current_user: dict = Depends(get_current_user),
):
    """List all consent records (active and revoked) for a patient."""
    validate_safe_param(patient_or_contact, "patient_id")

    patient_id = patient_or_contact
    profile = _me.get_patient_by_id(patient_or_contact)
    if profile is None:
        resolved = get_patient_id_from_chat_name(patient_or_contact)
        if resolved:
            patient_id = resolved
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Patient not found: {patient_or_contact}",
            )

    active = _me.get_active_consents(patient_id)
    history = _me.get_consent_history(patient_id)

    return {
        "patient_id": patient_id,
        "active": active,
        "history": history,
    }
