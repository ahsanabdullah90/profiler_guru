# Profile_Guru

> **📸 Instagram DM Analysis & Psychological Profiler**
>
> An AI-powered tool that syncs, imports, indexes, and analyzes Instagram Direct Messages. Powered by a RAG (Retrieval-Augmented Generation) pipeline using ChromaDB and Google Gemini, with automatic image captioning and audio transcription.

---

## Features

| Feature                    | Description                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Human-Paced Live Sync**  | Connects to the Instagram API and sequentially polls for new DMs using circadian sleep schedules and activity pauses to safeguard accounts. |
| **Historical Data Import** | Ingests Instagram data-export ZIPs (JSON format) with full media handling.                                     |
| **RAG-Powered Search**     | Context-augmented queries combining localized monthly markdown logs (within selectable range) and vector chunks. |
| **Personality Profiler**   | Generates psychological assessments from raw DMs over selected date ranges, with token metrics and PDF exports. |
| **Media Processing**       | Images are captioned by Gemini; voice clips are transcribed by faster-whisper — both fed into the RAG index.   |
| **Chat Browser**           | Browse raw monthly markdown logs per contact directly in the Streamlit UI.                                     |
| **Connection Depth Badge** | Analyzes daily message counts and evaluates relationships dynamically (Deep, Active, Casual, Dormant).        |
| **Connection Analytics**   | Graph daily history with interactive 14-day trend charts and compare weekly/monthly average volumes.           |
| **Settings Persistence**   | Dedicated settings interface to persist API keys, preferred AI engine, deep-scan defaults, and PDF layouts.   |
| **Task Mission Control**   | Real-time background task registry displaying progress bars, statistics, and enabling cancellation.            |

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Next.js Frontend                                     │
│                                 (frontend/src/...)                                     │
│   ┌────────────────────┐   ┌────────────────────┐   ┌──────────────────────────────┐   │
│   │    Main Dashboard  │   │  AI Hub Panel      │   │   Fuzzy Global Search        │   │
│   │   (Workspace.tsx)  │   │    (AIHub.tsx)     │   │   (GlobalSearch.tsx)         │   │
│   └─────────┬──────────┘   └─────────┬──────────┘   └──────────────┬───────────────┘   │
└─────────────┼────────────────────────┼─────────────────────────────┼───────────────────┘
              │                        │                             │
              │                 REST APIs / WebSockets               │
              ▼                        ▼                             ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FastAPI Backend                                      │
│                           (main_api.py / src/api/...)                                  │
│   ┌───────────────────────┐   ┌───────────────────────────┐   ┌────────────────────┐   │
│   │ REST & WS Endpoints   │   │ Application Engines       │   │ background Sync    │   │
│   │ • /api/contacts       │   │ • RAGEngine               │   │ • Sequential sync  │   │
│   │ • /api/reports        │   │ • MetricsEngine           │   │ • Circadian interval│  │
│   │ • /api/status (WS)    │   │ • MediaProcessor (Gemini) │   │ • Task Tracker     │   │
│   └───────────────────────┘   └─────────────┬─────────────┘   └─────────┬──────────┘   │
└─────────────────────────────────────────────┼───────────────────────────┼──────────────┘
                                              ▼                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                     Storage Layer                                      │
│                                                                                        │
│  ┌──────────────────────┐    ┌───────────────────────┐    ┌─────────────────────────┐  │
│  │  StorageManager      │    │  SQLite Database      │    │  ChromaDB Vector Store  │  │
│  │  storage_manager.py  │    │  psych_profiles.db    │    │  chroma_db/             │  │
│  │                      │    │                       │    │                         │  │
│  │  Writes monthly      │    │  Stores daily message │    │  Persistent vector store│  │
│  │  markdown logs to    │    │  counts under WAL     │    │  with cosine similarity │  │
│  │  chats/<name>/       │    │  mode (thread-safe)   │    │  indexing for RAG       │  │
│  └──────────────────────┘    └───────────────────────┘    └─────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

#### Next.js Frontend — UI Layer (`frontend/src/`)
The Next.js single-page application. Provides a premium, glassmorphic dark-theme interface with four contact-level workspace panels and a unified dashboard:
1. **💬 Conversation History (`Workspace.tsx`)** — Renders monthly `.md` logs with voice message players and a bilingual Urdu/English keyword filter.
2. **👤 Personality Assessment (`AIHub.tsx`)** — Contact psychological profiler supporting start/end month filtering, presets (Last Month, Last 3 Months, Custom), real-time token metrics, and report downloads.
3. **📊 Connection Analytics (`Workspace.tsx`)** — Visualizes relationship metrics using interactive 14-day daily message trend line charts and calculates weekly vs. monthly daily averages.
4. **🤖 Ask AI (`AIHub.tsx`)** — Contact-scoped history search incorporating range boundaries and hybrid search merging. Also displays sync status and background ingestion metrics.
5. **⚙️ Credentials Integration (`Header.tsx` & `StatusBar.tsx`)** — Comprehensive control panel supporting masked API credentials, AI Engine provider switches, and active sync managers. Handles Direct challenge warning panels for verification and login retries.

#### FastAPI Backend — API Layer (`main_api.py` / `src/api/`)
High-performance REST and WebSocket API service orchestrating all database, media processing, sync, and RAG engines.

#### `src/engine/rag_engine.py` — RAG Engine
- Initializes a **ChromaDB PersistentClient** (`chroma_db/`) with a single collection `instagram_messages` (cosine similarity metric).
- **Indexing** — Splits markdown messages by `---` separators, parses stable `<!-- chunk_id: ... -->` comments as document IDs to align vectors precisely, and falls back to MD5-of-content for older blocks.
- **Stable Transcription Updates** — Deletes old placeholder chunks accurately using a bug-free stable chunk ID mapping before indexing transcribed blocks.
- **Non-Blocking Database Vacuum** — Implements `vacuum_orphaned_vectors()` performing a dual-index scan (chunk comments + legacy hashes) to batch-delete orphaned ChromaDB records in a delayed background daemon thread.
- **Snippet Fetching** — Implements `fetch_markdown_snippets` with lexicographical range matching over YYYY_MM filename patterns.
- **Token Estimation** — Computes prompt sizes utilizing exact tiktoken BPE token counting.

#### `src/engine/llm_dispatcher.py` — LLM Dispatcher
- Dynamic LLM router evaluating token sizes and engine preferences.
- Processes contexts up to `64,000` tokens privately using local Ollama (`gemma-3-4b`), gracefully routing larger payloads or force-cloud requests to Cloud Gemini (`gemini-1.5-flash`).
- Protects runtime operations by performing key configurations dynamically and raising informative, non-crashing interface errors.

#### `src/engine/settings_manager.py` — Settings Manager
- Core persistence utility reading and writing configurations to `exports/settings.json`.
- Manages AI provider preferences, cloud keys, report layout orders, and deep scan defaults.
- Synchronizes values dynamically to the global configuration object to reflect settings changes immediately.

#### `src/engine/report_generator.py` — PDF Report Generator
- Assembles professional, multi-page psychological reports using **ReportLab** and **Matplotlib**.
- Visualizes bilingual emotional sentiment trends over time (line plot) and monthly messaging volumes (bar chart).
- Incorporates a clean markdown-to-pdf flowable parser and light-gray alternating background tables rendering raw conversation snippets.
- Restructures output pages dynamically to respect the user's preferred layout ordering.

#### `src/engine/instagram_sync.py` — Live Sync
- Coordinates the live syncing loop. Authenticates via `instagrapi.Client` with encrypted session file caching, preserving device fingerprints across cookie refreshes on session expiration.
- **Sequential & Human-Paced Ingestion** — Sequentially polls threads with randomized inter-thread delays (2–5 seconds) and inter-message delays (0.5–1.5 seconds) to simulate natural human scroll behavior and protect accounts from anti-bot blocks.
- **Circadian Sync Timing** — Computes Gaussian-jittered sync intervals (daytime ~5 min, nighttime ~15 min) and skips nighttime syncs (10% chance) to simulate sleep patterns.
- **User Activity Avoidance** — Pauses background sync for 30 seconds if user UI activity is detected, avoiding API resource contention.
- **Progressive Error Backoffs** — Implements exponential backoffs on sync failures, entering a 30-minute cooling-off period after 3 consecutive failures.
- **Verification Recovery** — Catches `challenge_required` login errors, extracts the absolute challenge URL, and routes it to the Streamlit UI.
- **Background Vacuum** — Triggers a non-blocking vector store vacuum operation 60 seconds after startup.
- Operates under the control of `SyncManager` using a process-wide `stop_event` pass for immediate and graceful cancellation.

#### `src/engine/data_importer.py` — Historical Import
- Manages unzipped Instagram data-export folder ingestion, resolving standard layouts automatically.
- Parses `message_*.json` files, corrects latin-1 string encoding errors, copy-processes audio voice notes, writes monthly log formats, registers progress to the SQLite metrics database, and performs batch indexing to ChromaDB.

#### `src/engine/metrics_engine.py` — Connection Metrics Engine
- Manages the SQLite database (`psych_profiles.db`) in **Write-Ahead Logging (WAL) mode** for concurrent, thread-safe access.
- Logs daily message counts per contact, treating text and audio messages equally.
- Computes weekly and monthly **true daily averages** (taking inactive days into account mathematically).
- Performs metrics exports to standard **CSV** and **JSON** formats.

#### `src/engine/media_processor.py` — Media Processing
- **Audio Transcription** — Lazily loads the `faster-whisper` library and transcribes localized audio voice notes (supporting bilingual English/Urdu speech).

#### `src/storage/storage_manager.py` — File System Storage
- Organizes localized data structures under:
  ```
  chats/<contact_name>/
  ├── Chats/        ← Monthly markdown logs (YYYY_MM.md)
  └── Audio/        ← Downloaded voice clips
  ```
- Appends formatted markdown blocks thread-safely using local file write locks.
- Generates and appends stable `<!-- chunk_id: <hash> -->` comments at the end of each message block to enable stable vector indexing.

#### `src/utils/task_tracker.py` — Background Task Tracker
- Thread-safe task registry singleton that monitors background tasks (live sync, historical import, database backfill).
- Maps task progress percentages, active files, statuses, and coordinates graceful thread cancellation requests.

#### `src/utils/config.py` — Configuration
- Loads settings from `.env` via `python-dotenv`, defining paths (hardened to `%LOCALAPPDATA%/Profile_Guru` on Windows), thread limits, sync intervals, and API keys.

#### `src/utils/logger.py` — Logging
- Configures rotating file and console logging to output execution details to `app.log`.

---

## Tech Stack

| Layer        | Technology                  | Purpose                                              |
| ------------ | --------------------------- | ---------------------------------------------------- |
| **Frontend** | Next.js (React, TS, Tailwind, Zustand) | Highly responsive, glassmorphic dark-theme portal dashboard |
| **Backend**  | FastAPI (Python, REST, WS)  | High-performance API orchestration layer             |
| **LLM**      | Google Gemini 1.5 Flash     | Chat analysis, image captioning, profile generation  |
| **Vectors**  | ChromaDB (PersistentClient) | Cosine-similarity vector search over message chunks  |
| **ASR**      | Google Gemini ASR & Whisper | High-accuracy cloud ASR with local Whisper fallback   |
| **PDF Lib**  | reportlab                   | Programmatic multi-page document layout compilation  |
| **Charts**   | Matplotlib & Recharts       | Graphic line trend lines and interactive UI charts   |
| **IG API**   | instagrapi                  | Instagram login, DM fetch, media download            |
| **Config**   | python-dotenv               | `.env` file loading                                  |
| **Testing**  | pytest                      | Unit / integration / E2E test suite with full mocking |

---

## Data Flow

### 1. Live Sync Flow

```
Instagram API ──► InstagramSync.fetch_new_messages(stop_event)
                    │
                    ├─ For each active thread (sequential, 2–5 s delay):
                    │   ├─ Filter out shared reels and unsupported media attachments
                    │   ├─ For each new supported message (0.5–1.5 s delay):
                    │   │   ├─ If voice note → download → MediaProcessor.transcribe_audio()
                    │   │   ├─ StorageManager.save_message() → chats/<name>/Chats/YYYY_MM.md
                    │   │   │    (Appends stable <!-- chunk_id: ... --> comment)
                    │   │   ├─ MetricsEngine.increment_message() → SQLite psych_profiles.db
                    │   │   └─ RAGEngine.add_messages_batch()  ──► ChromaDB upsert
                    │   │
                    │   └─ Record Sync Run completion timestamp for contact
                    │
                    └─ Sleep(Circadian Interval + Jitter) ──► repeat
```

### 2. Historical Import Flow

```
Instagram Data Export ZIP (unzipped)
    │
    └─ InstagramDataImporter.import_from_json()
         │
         ├─ Resolve Inbox structure and perform preflight directory checks
         ├─ For each chat folder in inbox/:
         │   ├─ Read message_*.json files
         │   ├─ Fix latin-1/UTF-8 encoding issues
         │   ├─ Copy and transcribe audio notes → chats/<name>/Audio/
         │   ├─ StorageManager.save_message() → chats/<name>/Chats/YYYY_MM.md
         │   ├─ MetricsEngine.increment_message() → SQLite psych_profiles.db
         │   └─ Accumulate in-memory batch
         │
         └─ Batch upsert to ChromaDB every 50 messages
```

### 3. RAG Query Flow

```
User Query ──► Streamlit Ask AI
                 │
                 ├─ RAGEngine.fetch_markdown_snippets(range) ──► Selected Month Text
                 ├─ ChromaDB.query(top-20, chat_filter)      ──► Cosine Chunks
                 ├─ Concatenate Sources & Estimate Tokens
                 └─ LLMDispatcher.dispatch()                 ──► Synthesized Answer
```

### 4. Profile Generation Flow

```
Contact Selection ──► Start/End Month Dropdowns
                        │
                        ├─ RAGEngine.fetch_markdown_snippets(range)
                        ├─ RAGEngine.estimate_token_count()
                        ├─ LLMDispatcher.dispatch()
                        │    ├─ Local Ollama (gemma-3-4b) if <= 64k tokens
                        │    └─ Cloud Gemini (gemini-1.5-flash) if > 64k or forced
                        ▼
                  Psychological Assessment Renders
```

### 5. PDF Generation Flow

```
Trigger Compile PDF ──► ReportGenerator.create_assessment_pdf()
                          │
                          ├─ Query monthly message volumes & sentiment score trends
                          ├─ Matplotlib generates frequency & sentiment trend charts
                          ├─ Extract latest N raw conversation snippets
                          ├─ Flowable Story builds cover, metadata, and custom H1/bullet styles
                          ├─ Appends textual profile, charts, and raw snippet tables
                          └─ SimpleDocTemplate builds file & applies running footer/header
```

---

## Project Structure

```
profiler_guru/
├── run.bat                          # Batch launcher (kills stale ports, health-checks, boots Next.js + FastAPI)
├── main_api.py                      # FastAPI entry point — REST & WebSocket services
├── requirements.txt                 # Python dependencies (includes matplotlib, reportlab)
├── .env.example                     # Template for environment variables
├── AGENTS.md                        # Agent coding standards & documentation policy
├── legacy/                          # Legacy Streamlit UI, entry point, and password tests
│
├── frontend/                        # Next.js Frontend (React, TS, Zustand, Tailwind, Recharts)
│
├── src/
│   ├── __init__.py
│   ├── app/
│   │   └── __init__.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── rag_engine.py            # ChromaDB RAG core, snippet range fetcher, token heuristics
│   │   ├── llm_dispatcher.py        # Token-based LLM router (Ollama vs. Cloud Gemini)
│   │   ├── settings_manager.py      # JSON settings loader, saver, and Config sync
│   │   ├── report_generator.py      # Programmatic PDF Report compiler using ReportLab & Matplotlib
│   │   ├── instagram_sync.py        # Live DM sync loop and SyncManager
│   │   ├── data_importer.py         # Historical Instagram export importer
│   │   ├── metrics_engine.py        # WAL-mode SQLite database & analytics exporter
│   │   └── media_processor.py       # Audio voice transcription (Gemini Cloud + local Whisper)
│   ├── storage/
│   │   ├── __init__.py
│   │   └── storage_manager.py       # Local file system monthly markdown log organizer
│   └── utils/
│       ├── __init__.py
│       ├── config.py                # .env loader, path resolver, & config singleton
│       ├── logger.py                # Console & rotating file logger setup
│       ├── sync_locks.py            # Process-wide IMPORT_LOCK singleton for background sync
│       └── task_tracker.py          # Thread-safe background task tracking registry
│
├── tests/
│   ├── README.md                    # Testing documentation
│   ├── ISSUES_LOG.md                # Known bugs & architectural issues
│   ├── conftest.py                  # Shared pytest fixtures
│   ├── test_media_processor.py      # MediaProcessor ASR & fallback unit tests
│   ├── test_personality_gui.py      # Personality Assessment & RAG Overhaul unit tests
│   ├── test_storage.py              # StorageManager unit tests
│   ├── test_rag_engine.py           # RAGEngine unit tests
│   ├── test_importer.py             # Data importer integration tests
│   ├── test_sync.py                 # Instagram sync tests
│   ├── test_e2e.py                  # End-to-end flow tests
│   └── test_broken.py               # Edge-case & error-handling tests
│
├── chats/                           # Local message storage (organizes monthly markdown)
│   └── <contact_name>/
│       ├── Chats/                   # Monthly markdown logs (YYYY_MM.md)
│       └── Audio/                   # Synced voice clips (.mp3)
│
└── chroma_db/                       # ChromaDB persistent vector store
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- (Optional) CUDA-capable GPU for faster whisper inference

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/profiler_guru.git
cd profiler_guru

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

| Variable             | Required | Default  | Description                              |
| -------------------- | -------- | -------- | ---------------------------------------- |
| `GOOGLE_API_KEY`     | Yes      | —        | Google AI Studio API key for Gemini      |
| `INSTAGRAM_USERNAME` | No       | —        | Instagram account username               |
| `INSTAGRAM_PASSWORD` | No       | —        | Instagram account password               |
| `CHATS_DIR`          | No       | `chats`  | Root directory for local chat storage    |
| `SYNC_INTERVAL`      | No       | `300`    | Background sync interval in seconds      |
| `USE_GPU`            | No       | `false`  | Set to `true` to use CUDA for whisper    |
| `OLLAMA_LIST_TIMEOUT` | No      | `10`     | Timeout for fetching local Ollama models  |
| `OLLAMA_GENERATE_TIMEOUT` | No  | `120`    | Timeout for local LLM text generation     |

### Running the App

To run the modern decoupled portal (Next.js & FastAPI):

Double-click or run `run.bat` from any directory or terminal:
```bash
run.bat
```

This batch launcher ensures high robustness:
* **Absolute Path Independence**: Uses the `%~dp0` variable to locate the virtual environment (`.venv`) and directories absolutely, preventing path resolution failures when executed from different working directories.
* **Process Cleanup**: Automatically kills existing stale processes listening on port `8000` (FastAPI) and port `3000` (Next.js).
* **Active Health-Check Polling**: Instead of a blind sleep timeout, it actively queries the newly introduced `/api/health` endpoint on the FastAPI server until the backend is fully initialized.
* **Synchronized Browser Launch**: Opens the browser and points it to `http://localhost:3000` only after the backend is ready, avoiding initial connection errors.

To shut down, simply close the minimized backend and frontend terminal windows.

*Note: The legacy Streamlit-based interface and its supporting files have been moved to the `legacy/` directory and are no longer part of the active web application.*


---

## Testing

Comprehensive tests are available in the `tests/` directory. For detailed instructions, see the [Testing Documentation](tests/README.md).

```bash
# Run the full test suite
PYTHONPATH=. python -m pytest tests/

# Run a specific test file
PYTHONPATH=. python -m pytest tests/test_rag_engine.py
```

All external services (Instagram API and Gemini AI) are fully mocked in tests.

---

## Known Issues

See [tests/ISSUES_LOG.md](tests/ISSUES_LOG.md) for a list of identified bugs and architectural concerns, including:

1. **Invalid timestamp handling** in `StorageManager.save_message()`.
2. **Hardcoded ChromaDB path** in `RAGEngine.__init__()`.
3. **Partial initialisation** of `MediaProcessor` when GPU/API dependencies are missing.

---

## Documentation Policy

This project maintains strict synchronisation between documentation and testing. Any changes to documentation must be accompanied by a review of the test suite. See [AGENTS.md](AGENTS.md) for full contributor guidelines.
