# Database Schema & Migrations

Profile Guru uses SQLite as its primary metadata store (`psych_profiles.db`), operating in Write-Ahead Logging (WAL) mode to handle concurrent multi-threaded writes (such as live WhatsApp bridge ingestion alongside user UI edits).

---

## 1. Database Table Reference

```
     ┌────────────────────────┐         ┌────────────────────────┐
     │    client_profiles     │◄───────┐│    patient_consents    │
     │  (Primary Patient Rec) │         ││  (HIPAA Gating Logs)   │
     └───────────┬────────────┘         └└───────────┬────────────┘
                 │                                   │
                 ├─────────────────┬─────────────────┤
                 ▼                 ▼                 ▼
     ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐
     │     clinical_notes     │ │   assessment_history   │ │     session_audio      │
     │  (Session Annotations) │ │ (Behavioral Profiles)  │ │ (Transcribed Sessions) │
     └────────────────────────┘ └────────────────────────┘ └────────────────────────┘
```

### Table: `client_profiles`
Represents the canonical identity of a client or patient.
- `chat_name` (TEXT, PRIMARY KEY): The unique directory-safe string identifier (often their Instagram handle or WhatsApp contact name).
- `display_name` (TEXT)
- `email` (TEXT)
- `mobile` (TEXT)
- `whatsapp` (TEXT): Normalized WhatsApp phone number (if linked).
- `instagram_handle` (TEXT): Instagram identifier.
- `photo_path` (TEXT)
- `updated_at` (TEXT)
- `patient_id` (TEXT): Unique clinical UUID.
- `dob` (TEXT): Date of birth.
- `mrn` (TEXT): Medical Record Number.
- `consent_active` (INTEGER): `1` if the patient has active consents; `0` otherwise.

### Table: `patient_consents`
Records attested HIPAA or research consent agreements.
- `consent_id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `patient_id` (TEXT, NOT NULL)
- `consent_type` (TEXT, NOT NULL): e.g., `chat_analysis`, `audio_recording`, or `clinical_assessment`.
- `attested_by` (TEXT, DEFAULT 'practitioner')
- `consent_version` (TEXT, NOT NULL)
- `attested_at` (TEXT, NOT NULL)
- `revoked_at` (TEXT, NULLABLE)
- `notes` (TEXT)

### Table: `clinical_notes`
Contains practitioner observations and clinical assessments.
- `note_id` (TEXT, PRIMARY KEY): UUID.
- `patient_id` (TEXT, NOT NULL)
- `contact_name` (TEXT, NOT NULL)
- `session_date` (TEXT, NOT NULL)
- `note_type` (TEXT, DEFAULT 'free')
- `note_text` (TEXT, NOT NULL)
- `consent_version` (TEXT)
- `created_at` (TEXT, NOT NULL)
- `updated_at` (TEXT, NOT NULL)
- `revised_from` (TEXT, NULLABLE): For revision history tracking.
- `deleted_at` (TEXT, NULLABLE)

### Table: `assessment_history`
Stores metadata and file locations for generated psychological profiles.
- `assessment_id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `contact_name` (TEXT, NOT NULL): Maps to `chat_name`.
- `generated_at` (TEXT, NOT NULL)
- `framework_id` (TEXT, NOT NULL)
- `model_name` (TEXT, NOT NULL)
- `start_month` (TEXT, NOT NULL)
- `end_month` (TEXT, NOT NULL)
- `file_path` (TEXT): Path to saved markdown profile.
- `assessment_json` (TEXT): JSON containing dimensions scores, citations, and metadata.

### Table: `session_audio`
Tracks transcripts and status for longer session recordings.
- `session_id` (TEXT, PRIMARY KEY): UUID.
- `patient_id` (TEXT, NOT NULL)
- `file_path` (TEXT, NOT NULL)
- `status` (TEXT): `pending`, `transcribing`, `completed`, or `failed`.
- `duration_sec` (INTEGER)
- `transcript` (TEXT)
- `created_at` (TEXT, NOT NULL)
- `transcribed_at` (TEXT)
- `error_message` (TEXT)

### Table: `connection_metrics`
Logs historical daily counts (used for Recharts analytics graphs).
- `chat_name` (TEXT)
- `date` (TEXT): Format `YYYY-MM-DD`.
- `message_count` (INTEGER)
- `audio_count` (INTEGER)
- `word_count` (INTEGER)
- PRIMARY KEY (`chat_name`, `date`)

### Table: `contact_metadata`
Stores overall metrics for fast listing.
- `chat_name` (TEXT, PRIMARY KEY)
- `message_count` (INTEGER)
- `audio_count` (INTEGER)
- `last_message_time` (INTEGER): Epoch timestamp.
- `name_hash` (TEXT)
- `first_message_time` (INTEGER)
- `system_imported` (INTEGER)

### Table: `contact_platforms`
Associates contacts with platforms (for merging tracking).
- `chat_name` (TEXT)
- `platform` (TEXT): `instagram` or `whatsapp`.
- `message_count` (INTEGER)
- `last_seen` (INTEGER)
- PRIMARY KEY (`chat_name`, `platform`)

### Table: `pending_merges`
Fuzzy name matches waiting for practitioner confirmation.
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `new_chat_name` (TEXT)
- `existing_chat_name` (TEXT)
- `reason` (TEXT)
- `similarity` (REAL)
- `created_at` (TEXT)
- `resolved_at` (TEXT)
- `action` (TEXT): `pending`, `merged`, or `dismissed`.

---

## 2. Version 2 Migrations

During startup initialization, the `MetricsEngine` executes migrations on the SQLite connection. If the database file is upgraded from a pre-clinical version:
- The script adds columns to `client_profiles` using `ALTER TABLE client_profiles ADD COLUMN ...` statements wrapped in exception-catching blocks.
- Columns added: `patient_id` (TEXT), `dob` (TEXT), `mrn` (TEXT), and `consent_active` (INTEGER DEFAULT 0).
- **UUID Backfilling:** Any existing records that have a null `patient_id` are automatically assigned a unique 12-character UUID prefix (`str(uuid.uuid4())[:12]`) to preserve schema integrity.

---

## 3. SQLite Concurrency (WAL Mode)

To allow FastAPI background threads and the Node listener to write concurrently without lock errors (`sqlite3.OperationalError: database is locked`):
- The database is opened with `PRAGMA journal_mode=WAL;` and `PRAGMA synchronous=NORMAL;`.
- SQLite's Write-Ahead Logging allows multiple readers to read while another thread is writing to a separate WAL file, which is checkpointed back to the main DB periodically.
- Additionally, the `MetricsEngine` implements a thread-safe re-entrant write lock (`self._write_lock = threading.RLock()`) to secure critical database commit transactions.
