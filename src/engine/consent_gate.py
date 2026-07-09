"""Consent gate — ensures patient data is only used with active consent.

Every data-access path (chat import, RAG search, assessment, audio upload) must
call one of these functions before operating on patient data.

Consent types:
- chat_analysis: IG/WhatsApp import, RAG search, message-level analysis
- audio_recording: session audio upload and transcription
- clinical_assessment: profile generation and report creation
"""

from src.engine.metrics_engine import MetricsEngine
from src.utils.logger import logger

_me = MetricsEngine()


class ConsentRequiredError(Exception):
    """Raised when an operation requires patient consent that is not active."""
    pass


CONSENT_TYPES = frozenset(["chat_analysis", "audio_recording", "clinical_assessment"])


def require_consent(patient_id: str, consent_type: str) -> None:
    """Check that the patient has active consent for the given type.

    Raises ConsentRequiredError if consent is missing or revoked.
    """
    if consent_type not in CONSENT_TYPES:
        raise ValueError(f"Unknown consent type: {consent_type}")

    if not _me.has_active_consent(patient_id, consent_type):
        logger.warning(
            f"Consent check failed: patient={patient_id}, type={consent_type}"
        )
        raise ConsentRequiredError(
            f"Patient {patient_id} does not have active consent "
            f"for '{consent_type}'. Operation blocked."
        )


def check_consent(patient_id: str, consent_type: str) -> bool:
    """Non-raising check — returns True if consent is active."""
    if consent_type not in CONSENT_TYPES:
        return False
    return _me.has_active_consent(patient_id, consent_type)


def get_patient_id_from_chat_name(chat_name: str) -> str | None:
    """Resolve a chat_name (IG handle) to a patient_id.

    Returns None if no patient record exists with this chat_name.
    """
    profile = _me.get_client_profile(chat_name)
    if profile and profile.get("patient_id"):
        return profile["patient_id"]
    return None
