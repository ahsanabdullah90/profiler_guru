# Profile Guru: Executive Summary & Overview

> **📸 Multichannel Relationship Analytics & Clinical Behavioral Profiler**
>
> Profile Guru is a secure, HIPAA-compliant intelligence portal that ingests, indexes, and analyzes conversational data from Instagram Direct Messages and WhatsApp. By combining deterministic clinical questionnaires (PHQ-9, GAD-7, BHS), a hybrid RAG (Retrieval-Augmented Generation) pipeline, and strict consent gating, Profile Guru empowers practitioners to build comprehensive behavioral assessments and relationship depth profiles.

---

## High-Level Capabilities

### 1. Multichannel Data Ingestion
- **Instagram DM Exports:** Import and parse standard Instagram data ZIP files in JSON format, handling unicode/latin-1 normalization, and extracting media references.
- **WhatsApp Bridge:** Run a Puppeteer-based active listener (`listener.js`) that captures live WhatsApp message streams and downloads audio attachments.
- **Bilingual Audio Processing:** Auto-transcribe voice clips (English & Urdu) using Google Gemini Cloud ASR with local `faster-whisper` fallback.

### 2. Clinical Consent & Data Gating
- **Ethical Safeguards:** Enforce strict consent validation across all analytical pipelines (chat imports, semantic RAG search, clinical profiling, and audio uploads).
- **Consent Attestations:** Keep historic logs of consent forms (`patient_consents` table), allowing practitioners to attest or revoke consents at any time.

### 3. Advanced Behavioral Profiling
- **Orchestrated Assessment Pipeline:** Seamlessly route profiling tasks to the best LLM engine based on model classification.
- **Single-Pass (Large Models):** Execute rich, contextual profiling on models like Google Gemini 1.5 Flash.
- **Modular Sequential Synthesis (Small Models):** Programmatically run step-by-step analytical passes on lightweight local LLMs (e.g. Ollama `gemma-3-4b`) to avoid context overload.
- **Reference Grounding:** Augment LLM prompts using clinical literature retrieved from the internal knowledge base.

### 4. Deterministic Clinical Scoring
- **Standardized Instruments:** Administer and deterministically score Patient Health Questionnaire-9 (PHQ-9), Generalized Anxiety Disorder-7 (GAD-7), and Beck Hopelessness Scale (BHS).
- **History Tracking:** Log all scores and responses in the database to track patient progress over time.

### 5. Premium UI/UX & Analytical Dashboard
- **Glassmorphic Theme:** An AA-compliant design token system supporting custom Dark and Light modes.
- **Three-Pane Workspace:** Combines a contact list with connection indicators, a chat browser with keyword highlights, and an interactive analytics view.
- **Data Visualization:** Recharts-powered trend lines wrapped in `<ChartFrame>` featuring data-table fallbacks and CSV exports.
- **Power-User Tooling:** Resizable Inspector panel (tags, clinical notes, star flags) toggled via `Ctrl/Cmd+I` and a keyboard shortcut cheatsheet (`?`).

---

## Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Next.js (React, TS, Tailwind, Zustand) | Premium glassmorphic workspace and credential management. |
| **Backend** | FastAPI (Python, Uvicorn, SSE) | High-performance API orchestration layer. |
| **Database** | SQLite (WAL-Mode, Thread-Safe) | Persistent store for patient profiles, consent, notes, and metrics. |
| **Vector DB** | ChromaDB (PersistentClient) | Cosine-similarity indexing of conversation chunks for RAG. |
| **LLM Router** | Google Gemini 1.5 Flash & Local Ollama | Assessment generation and contextual search. |
| **ASR Engine** | Gemini ASR / Faster-Whisper | Dual-mode speech-to-text for audio voice clips. |
| **PDF Engine** | ReportLab & Matplotlib | Programmatic generation of multi-page PDF reports. |
| **Bridge Client** | Node.js / Puppeteer / `whatsapp-web.js` | Headless bridge for live WhatsApp message capture. |
