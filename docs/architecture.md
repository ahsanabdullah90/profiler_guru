# System Architecture

Profile Guru uses a modern, decoupled client-server architecture. The frontend is built as a single-page Next.js application, communicating with a FastAPI backend via REST endpoints, Server-Sent Events (SSE), and WebSockets.

---

## Architectural Block Diagram

```
       ┌────────────────────────────────────────────────────────┐
       │                   Next.js Frontend                     │
       │                                                        │
       │  ┌───────────────────────┐   ┌──────────────────────┐  │
       │  │ Workspace Dashboard   │   │  AI Hub Panel        │  │
       │  │ (Workspace.tsx)       │   │  (AIHub.tsx)         │  │
       │  └───────────┬───────────┘   └──────────┬───────────┘  │
       │              │                          │              │
       │              └────────────┬─────────────┘              │
       │                           ▼                            │
       │                  Zustand Global Stores                 │
       │      (auth, ui, contacts, rag, status, task, tags)     │
       └───────────────────────────┬────────────────────────────┘
                                   │
                         REST APIs / WebSockets
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │                   FastAPI Backend                      │
       │                                                        │
       │   ┌────────────────────────────────────────────────┐   │
       │   │              APIs & Route Handlers             │   │
       │   │  • /api/v1/contacts    • /api/v1/consent       │   │
       │   │  • /api/v1/clinical    • /api/v1/rag           │   │
       │   │  • /api/v1/inspector   • /api/v1/whatsapp      │   │
       │   └────────────────────────┬───────────────────────┘   │
       │                            │                           │
       │                            ▼                           │
       │   ┌────────────────────────────────────────────────┐   │
       │   │              Application Engines               │   │
       │   │  • RAGEngine           • MetricsEngine         │   │
       │   │  • LLMDispatcher       • MediaProcessor        │   │
       │   │  • SettingsManager     • TranscriptionQueue    │   │
       │   └────────────────────────┬───────────────────────┘   │
       └────────────────────────────┼───────────────────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
       ┌───────────────────────────────────┐ ┌──────────────────┐
       │          Storage Layer            │ │    ChromaDB      │
       │                                   │ │  Vector Store    │
       │  • StorageManager (Markdown logs) │ │                  │
       │  • InspectorStore (JSON tags)     │ │  • Cosine index  │
       │  • SQLite DB (WAL clinical data)  │ │  • tenant_id     │
       └───────────────────────────────────┘ └──────────────────┘
```

---

## Module Responsibilities

### 1. API Route Layer (`src/api/`)
Orchestrates requests and feeds inputs to underlying service/engine components.
- **[api_contacts.py](file:///f:/Github/Profile-Guru/src/api/api_contacts.py):** Contact list, updates, and merging endpoints.
- **[api_whatsapp.py](file:///f:/Github/Profile-Guru/src/api/api_whatsapp.py):** Receives raw WhatsApp message payloads from the node bridge and initiates similar-contact matching.
- **[api_clinical.py](file:///f:/Github/Profile-Guru/src/api/api_clinical.py):** Handles questionnaire scoring, clinical notes creation, and session audio uploads.
- **[api_consent.py](file:///f:/Github/Profile-Guru/src/api/api_consent.py):** Logs practitioner-attested patient consents and revocations.
- **[api_rag.py](file:///f:/Github/Profile-Guru/src/api/api_rag.py):** Performs query-scoped semantic lookups and manages profiling requests.
- **[api_inspector.py](file:///f:/Github/Profile-Guru/src/api/api_inspector.py):** CRUD operations on patient-specific tags and clinical annotations.

### 2. Core Service Layer (`src/services/`)
Separates API routes from direct engine/storage operations.
- **[contacts_service.py](file:///f:/Github/Profile-Guru/src/services/contacts_service.py):** Retrieves contact metadata, calculates TRUE daily averages, and classifies relationship depth.
- **[contact_merge.py](file:///f:/Github/Profile-Guru/src/services/contact_merge.py):** Coordinates the multi-step merging of duplicate or matching platform records.

### 3. Application Engines (`src/engine/`)
- **[metrics_engine.py](file:///f:/Github/Profile-Guru/src/engine/metrics_engine.py):** Manages SQLite connections in Write-Ahead Logging (WAL) mode and updates user platform records.
- **[rag_engine.py](file:///f:/Github/Profile-Guru/src/engine/rag_engine.py):** Wraps ChromaDB. Segments and indexes logs using stable `<!-- chunk_id -->` annotations and BM25 keywords.
- **[llm_dispatcher.py](file:///f:/Github/Profile-Guru/src/engine/llm_dispatcher.py):** Dynamic prompt dispatcher. Routes local vs. cloud API keys and applies safety filters.
- **[media_processor.py](file:///f:/Github/Profile-Guru/src/engine/media_processor.py):** Translates voice notes to text using Google Gemini Cloud or local `faster-whisper`.
- **[consent_gate.py](file:///f:/Github/Profile-Guru/src/engine/consent_gate.py):** Gating layer raising `ConsentRequiredError` for un-attested patient data requests.

### 4. Storage & Utilities (`src/storage/` & `src/utils/`)
- **[storage_manager.py](file:///f:/Github/Profile-Guru/src/storage/storage_manager.py):** Writes thread-safe monthly conversation logs (`YYYY_MM.md`) with local file write locks.
- **[inspector_store.py](file:///f:/Github/Profile-Guru/src/storage/inspector_store.py):** Manages per-contact metadata in a thread-safe JSON store with atomic writes.
- **[config.py](file:///f:/Github/Profile-Guru/src/utils/config.py):** Parses `.env` variables and establishes system defaults.

---

## Evolution: Transition to Decoupled Import Mode

Originally, Profile Guru supported active polling of Instagram's API. This pattern was deprecated to secure the application against rate-limiting blocks and anti-bot bans:
- **No Background Pollers:** The backend no longer runs background syncing loops.
- **Import-Only Pipeline:** Historical logs are imported manually via ZIP files.
- **Event-Driven Bridges:** Live communications are captured via external listeners (like the WhatsApp Node Bridge) pushing messages to Backend endpoints.
