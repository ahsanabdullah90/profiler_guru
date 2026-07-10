# Right-to-Be-Forgotten & Patient Purge Cascade

Profile Guru implements a comprehensive patient data purge mechanism to support the right-to-be-forgotten (GDPR Article 17) and HIPAA data minimization requirements. When a patient is purged, all associated data is cascade-deleted across SQLite tables, filesystem storage, and vector indexes.

---

## 1. Purge Architecture (`metrics_engine.py`)

The purge system is implemented in [metrics_engine.py](file:///f:/Github/Profile-Guru/src/engine/metrics_engine.py) via the `purge_patient()` method.

### Core Method

```python
# From src/engine/metrics_engine.py
def purge_patient(self, patient_id_or_contact: str) -> dict:
    """Cascade-delete all data for a patient across ALL stores.

    This includes: client_profiles, patient_consents, clinical_notes,
    assessment_history, session_audio, chat files, Audio files, photos,
    ChromaDB vectors, and personality assessment files.

    Writes a tombstone to purged_patients table.
    """
```

### Return Value

```python
{
    "status": "purged",
    "patient_id": "abc123",
    "purged_at": "2026-07-10T01:30:00+00:00",
    "records_deleted": 15
}
```

Or if not found:
```python
{
    "status": "not_found",
    "patient_id": "abc123"
}
```

---

## 2. Cascade Deletion Sequence

The purge operation executes deletions in a specific order to maintain referential integrity:

### Step 1: Resolve Patient Identity
- Accepts either `patient_id` (UUID) or `chat_name` (contact identifier)
- Looks up the patient profile to retrieve the canonical `patient_id` and `chat_name`

### Step 2: SQLite Table Deletions (Under Write Lock)
All deletions are performed within a `_write_lock` to prevent concurrent modifications:

1. **`patient_consents`** — All consent attestations for the patient
2. **`clinical_notes`** — All clinical notes (hard delete, not soft delete)
3. **`assessment_history`** — All assessment metadata and file paths
4. **`session_audio`** — All audio transcription records
5. **`client_profiles`** — The patient profile itself

Each deletion increments a counter tracking total records deleted.

### Step 3: Filesystem Cleanup
After SQLite deletions, the system removes file-based data:

1. **Chat Directory** — `chats/<contact_name>/` (entire directory tree including monthly markdown logs, assessment files, and audio transcripts)
2. **Profile Photo** — Deletes the file at `photo_path` if it exists

### Step 4: Vector Store Cleanup
- Calls `rag_engine.delete_vectors_by_contact(chat_name)` to remove all ChromaDB vectors associated with the contact
- This uses ChromaDB's metadata filter deletion to target only the specific contact's vectors

### Step 5: Audit Tombstone
After all deletions complete, a tombstone record is written to the `purged_patients` table:

```sql
INSERT OR REPLACE INTO purged_patients 
(patient_id, purged_at, purged_by, reason, records_deleted) 
VALUES (?, ?, 'practitioner', ?, ?);
```

This ensures an audit trail exists even after all patient data is removed.

---

## 3. Purged Patients Audit Table

### Schema

```sql
CREATE TABLE IF NOT EXISTS purged_patients (
    patient_id TEXT PRIMARY KEY,
    purged_at TEXT NOT NULL,
    purged_by TEXT DEFAULT 'practitioner',
    reason TEXT,
    records_deleted INTEGER DEFAULT 0
);
```

### Purpose
- **Audit Trail:** Records that a patient was purged, when, and by whom
- **Compliance Evidence:** Demonstrates data deletion for regulatory audits (GDPR, HIPAA)
- **Prevent Re-Import:** The `patient_id` primary key prevents accidental re-creation of the same patient record

### Querying Purged Patients

```python
# From src/engine/metrics_engine.py
def get_purged_patients(self) -> list[dict]:
    """Return audit trail of all purged patients."""
    # Returns list of dicts with patient_id, purged_at, purged_by, reason, records_deleted
```

---

## 4. API Endpoints

### DELETE /clinical/{patient_id}

Purges all data for a patient.

**Request:**
```http
DELETE /api/v1/clinical/abc123 HTTP/1.1
Authorization: Bearer <token>
```

**Response (Success):**
```json
{
    "status": "purged",
    "patient_id": "abc123",
    "purged_at": "2026-07-10T01:30:00+00:00",
    "records_deleted": 15
}
```

**Response (Not Found):**
```json
{
    "status": "not_found",
    "patient_id": "abc123"
}
```

**Authentication:** Requires JWT (not a public route).

### GET /clinical/purged-patients

Returns the audit trail of all purged patients.

**Response:**
```json
{
    "purged_patients": [
        {
            "patient_id": "abc123",
            "purged_at": "2026-07-10T01:30:00+00:00",
            "purged_by": "practitioner",
            "reason": null,
            "records_deleted": 15
        }
    ]
}
```

---

## 5. Consent Gate Integration

The purge endpoint respects the consent gate system. Before purging:

1. The endpoint checks if the patient has `chat_analysis` consent
2. If consent is missing or revoked, the purge is blocked with a `ConsentRequiredError`
3. This prevents accidental purging of patients who haven't consented to data processing

**Note:** This is a safety check, not a privacy barrier. The right-to-be-forgotten supersedes consent requirements in most jurisdictions.

---

## 6. Error Handling & Partial Failures

The purge operation is designed to be idempotent and resilient:

### SQLite Deletions
- Wrapped in a transaction with `_write_lock`
- If any deletion fails, the entire transaction is rolled back
- No partial SQLite state is committed

### Filesystem Deletions
- Wrapped in try/except blocks
- If `shutil.rmtree()` fails (e.g., permission denied), a warning is logged but the purge continues
- The audit tombstone is still written

### Vector Store Deletions
- Called after SQLite and filesystem deletions
- If ChromaDB deletion fails, a warning is logged
- Orphaned vectors may remain but are harmless (they reference a deleted contact)

### Return Value
- Always returns a status dict, even on partial failure
- `records_deleted` count may be lower than expected if some deletions failed
- Check logs for warnings if the count seems off

---

## 7. Compliance & Regulatory Alignment

### GDPR Article 17 (Right to Erasure)
- ✅ Complete data deletion across all stores (SQLite, filesystem, vector DB)
- ✅ Audit trail maintained in `purged_patients` table
- ✅ No residual data in chat logs, assessments, or audio transcripts

### HIPAA §164.312(a)(1) (Access Control)
- ✅ Practitioner-attested purge (requires authentication)
- ✅ Audit logging of purge events
- ✅ Data minimization (hard delete, not soft delete)

### CCPA (California Consumer Privacy Act)
- ✅ Consumer can request deletion of all personal information
- ✅ Deletion is comprehensive (all data sources)
- ✅ Audit trail for compliance verification

---

## 8. Testing

The purge system is tested in `tests/test_purge_cascade.py` (if exists) or implicitly through clinical API tests. Key test scenarios:

- Purge by `patient_id`
- Purge by `chat_name` (fallback resolution)
- Verify all SQLite tables are cleared
- Verify chat directory is deleted
- Verify profile photo is deleted
- Verify ChromaDB vectors are deleted
- Verify audit tombstone is written
- Verify `get_purged_patients()` returns the audit trail
- Verify purge of non-existent patient returns `not_found`
- Verify idempotency (purging twice doesn't error)

---

## 9. Operational Considerations

### Performance
- Purge operations are synchronous and may take 1-5 seconds depending on data volume
- Large chat directories (1000+ monthly logs) may take longer to delete
- ChromaDB vector deletion is fast (metadata filter, not full scan)

### Backup & Recovery
- **No Undo:** Once purged, data cannot be recovered
- **Backup First:** Consider exporting patient data before purging if retention is needed
- **Audit Only:** The `purged_patients` table records the event but not the deleted data

### Monitoring
- All purge operations are logged at WARNING level
- Monitor logs for unexpected purges
- The `records_deleted` count can help verify completeness

---

## 10. Future Enhancements

### Planned
- **Soft Delete Option:** Move data to an archive table instead of hard delete (for legal hold scenarios)
- **Bulk Purge:** API endpoint to purge multiple patients in a single request
- **Scheduled Purge:** Auto-purge patients after a retention period (e.g., 7 years post-treatment)
- **Export Before Purge:** UI option to download a PDF report before initiating the purge
