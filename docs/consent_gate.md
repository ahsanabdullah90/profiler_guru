# Consent Gating & Data Protection

Profile Guru enforces a secure data protection boundary through a programmatic **Consent Gate** to guarantee that patient or client communication data is never accessed or processed without active practitioner-attested consent.

---

## 1. Consent Gate Architecture (`consent_gate.py`)

The consent checking functions are defined in [consent_gate.py](file:///f:/Github/Profile-Guru/src/engine/consent_gate.py) and serve as middleware gates throughout the backend:

```python
# From src/engine/consent_gate.py
def require_consent(patient_id: str, consent_type: str) -> None:
    """Check that the patient has active consent for the given type.

    Raises ConsentRequiredError if consent is missing or revoked.
    """
```

If a practitioner attempts to perform a search, upload audio, or generate a profile for a contact who does not have an active consent record on file, the system raises a `ConsentRequiredError` (which maps to an HTTP 400 response with error code `CLOUD_CONSENT_REQUIRED` or `CONSENT_REQUIRED`) and immediately aborts the operation.

---

## 2. Defined Consent Types

To support progressive disclosure and granular clinical permissions, consent is divided into three distinct types:

| Consent Type | Description | Operations Blocked If Missing |
| :--- | :--- | :--- |
| `chat_analysis` | Authorizes import and text parsing. | Instagram imports, live WhatsApp bridge ingestion, RAG search query, and keyword filtering. |
| `audio_recording` | Authorizes session and message audio. | Downloading WhatsApp voice notes, uploading session files, and enqueuing audio to transcription pipelines. |
| `clinical_assessment`| Authorizes behavioral profile generation. | LLM personality analysis, questionnaire submissions, and ReportLab PDF compilation. |

---

## 3. Database Attestation Records

When consent is granted, the backend records the event in the SQLite database:
- **Attestation Table (`patient_consents`):** Logs the `patient_id`, `consent_type`, the practitioner who attested the consent (`attested_by`), the forms version (`consent_version`), and the exact ISO timestamp (`attested_at`).
- **Profile State (`client_profiles`):** Updates the `consent_active` flag to `1` (True) for the patient.

### Revoking Consent
When consent is revoked:
- The system writes a `revoked_at` timestamp in the matching `patient_consents` row.
- If all consent types for that patient are revoked, it sets the patient's `consent_active` flag to `0`.
- Subsequent attempts to read or analyze files will raise a `ConsentRequiredError`.

---

## 4. API Endpoints

The gate is exposed to the frontend via the `/api/v1/consent` router in [api_consent.py](file:///f:/Github/Profile-Guru/src/api/api_consent.py):

- **Attest Consent (`POST /api/v1/consent/attest`):** Records a new active consent attestation.
- **Revoke Consent (`POST /api/v1/consent/revoke`):** Revokes an existing consent by marking it with a revoked timestamp.
- **List Consents (`GET /api/v1/consent/{patient_id}`):** Returns the history of active and revoked consent records.
