# WhatsApp Integration & Contact Merging

Profile Guru supports live message capture and historical synchronization from WhatsApp using an external Node-based bridge, which feeds directly into a programmatic merge and deduplication service.

---

## 1. Bridge Architecture (`listener.js`)

The bridge is implemented in [listener.js](file:///f:/Github/Profile-Guru/Whatsapp-Bridge/listener.js) and powered by `whatsapp-web.js` and `puppeteer`.

```
                       ┌─────────────────────────┐
                       │     WhatsApp Web        │
                       └────────────┬────────────┘
                                    │ (Scraped via Puppeteer)
                                    ▼
                       ┌─────────────────────────┐
                       │   Whatsapp-Bridge/      │
                       │     listener.js         │
                       └────────────┬────────────┘
                                    │ (POST JSON payload + base64 audio)
                                    ▼
                       ┌─────────────────────────┐
                       │    FastAPI Backend      │
                       │  /api/v1/whatsapp/ingest│
                       └─────────────────────────┘
```

- **Browser Emulation:** Puppeteer launches a headless Chrome instance that opens WhatsApp Web.
- **Authentication:** Emits a QR code event that is rendered as ASCII inside the terminal. Scanned via the mobile WhatsApp client, creating a persistent session using `LocalAuth` in the `Whatsapp-Bridge/Data/` folder.
- **Live Event Hook:** Listens to `message_create` events. If the message is a direct message (not from a group chat), it extracts metadata and forwards the payload.
- **Media Ingestion:** If the message is a voice note (`ptt` or `audio`), the script downloads the binary file, base64-encodes it, and sends it in the JSON request body.

---

## 2. Ingest API Payload (`/api/v1/whatsapp/ingest`)

The bridge POSTs JSON payloads mapping to the `WhatsAppIngestRequest` model in backend:

```json
{
  "timestamp": 1782230400,
  "from": "923001234567@c.us",
  "fromMe": false,
  "body": "Hello, how are you?",
  "type": "chat",
  "contact_name": "Ahsan Javed",
  "phone": "923001234567",
  "quoted_body": "Previous message text",
  "quoted_author": "Me",
  "media_data": "base64_encoded_audio_data_string_if_present",
  "media_mimetype": "audio/ogg"
}
```

### Phone Normalization
Before processing, raw phone identifiers (like `923001234567@c.us`) are sanitized to extract digits:
```python
_normalize_phone("923001234567@c.us")  # Returns "923001234567"
```

---

## 3. Contact Auto-Merging & Recommendation

Upon receiving a WhatsApp message, the backend performs dual-stage identity resolution to prevent duplicate contact cards.

### Stage 1: Auto-Merge by Phone (Implicit)
If the normalized phone number matches the `whatsapp` field of an existing profile in the database:
- The message is automatically written to the existing contact's directory.
- A platform metric record is updated to log both `instagram` and `whatsapp` activity.

### Stage 2: Fuzzy Name-Matching & Pending Merges (Explicit)
If no phone match is found, the backend flags the contact as new and initiates a similarity scan against all existing contacts using Gestalt Pattern Matching:
- **Threshold:** Set to **72%** similarity (`threshold=0.72`).
- **Trigger:** If a match is found (e.g., WhatsApp contact "Ahsan J." vs. Instagram contact "Ahsan Javed"), it writes a pending merge record to the `pending_merges` table.
- **UI Intervention:** A warning badge and option appears on the dashboard prompting the practitioner to **Confirm** or **Dismiss** the merge.

---

## 4. Programmatic Merge Engine (`contact_merge.py`)

When a practitioner confirms a merge suggestion, the system executes [merge_contacts()](file:///f:/Github/Profile-Guru/src/services/contact_merge.py#L12-L111) within a database write lock:

```python
# From src/services/contact_merge.py
def merge_contacts(primary_chat_name: str, secondary_chat_name: str) -> dict:
    # 1. Merge markdown monthly logs, deduplicating by chunk_id
    # 2. Relocate audio files from secondary to primary folders
    # 3. Purge secondary chats file directory
    # 4. Reassign SQLite DB rows: metadata, metrics, clinical notes, assessments, consents
    # 5. Purge secondary vectors from ChromaDB and re-index consolidated primary logs
    # 6. Mark pending merges as resolved
    # 7. Invalidate Redis cache
```

### Markdown Consolidation & Deduplication
- Messages are parsed block-by-block.
- The merge engine reads stable `<!-- chunk_id: <hash> -->` comments embedded at the end of message bubbles.
- Any message block in the secondary file whose `chunk_id` already exists in the primary file is discarded, preventing message duplication during merges.

### Database Updates
The engine transfers records in SQLite:
- Re-attributes daily message counts (`connection_metrics` table).
- Updates platforms flags to log both Instagram and WhatsApp handles.
- Re-associates clinical notes, consents, and assessment history to the primary contact's `patient_id`.
- Deletes the secondary contact metadata row from `contact_metadata`.

### Vector Store Synchronization
- Deletes all indexed vectors associated with the secondary contact from ChromaDB.
- Re-reads the primary contact's newly merged monthly markdown logs and batch-upserts them to ChromaDB.
