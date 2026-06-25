Version History

[0.9.1] – 2026-06-25
Added
- Collapsed multi-line HTML card structures to single-line strings via `.replace("\n", " ").strip()` to resolve Markdown indented-code-block rendering leaks.
- Unified and updated all project architecture diagrams, tech stack details, and module responsibilities in README.md to reflect WAL-mode SQLite metrics database, connection depth analytics, and background task Mission Control.

---

[0.9.0] – 2026-06-24
Added
- Persistent sync status tracking (`last_sync_run`) to record exact sync completion times for each contact.
- Real-time LLM indexing (RAG) progress indicators in the UI querying ChromaDB chunks vs. total messages.
- Monthly file-system storage batching (`YYYY_MM.md`) to prevent large log files and improve performance.
Changed
- Updated the entire project documentation (including README.md) to reflect monthly batching and sync/RAG progress features.
- Refactored storage, sync, RAG, and importer engines to support the new monthly log file structure.
Fixed
- Updated automated test suite to assert the new monthly log batching structure.

---

[0.8.1] – 2026-06-23
Fixed
- Rebuilt Instagram 2FA authentication flow: prevented stale/expired sessions from being reloaded during active 2FA challenges, added a clean client reset upon session expiration, and implemented robust fallback routing to handle both direct and two-step 2FA login mechanisms.
- Added comprehensive unit tests validating standard login, expired session cleanup, and 2FA login flows.

---

[0.8.0] – 2026-06-23
Added
- Contributor guidelines (CONTRIBUTING.md) and Code of Conduct (CODE_OF_CONDUCT.md).
- Pinned python package dependencies in requirements.txt.
Changed
- Finalized codebase docstrings across all modules (including storage_manager.py).
- Project documentation audit completed.

---

[0.7.0] – 2026-06-23
Changed
- Ingestion pipeline upgraded to use paginated thread sync (fetches up to 50 active threads).
- Deduplication keying switched to robust Instagram item_id and timestamp boundaries.
Added
- Concurrent ThreadPoolExecutor thread-fetching with thread-safety write locks.

---

[0.6.0] – 2026-06-23
Added
- Streamlit progress bars for JSON imports and spinner status messages for profiles.
- Sidebar sync status badge indicating running state and active LLM model.
- High-performance cached contact selector avoiding redundant disk reads.
- Bilingual search filter inside the Chat Browser tab (filtering message blocks).

---

[0.5.0] – 2026-06-23
Added
- Graceful background sync thread manager (SyncManager) with atexit exit hooks.
- State persistence (last_sync.json) to prevent message duplication across restarts.
- Global exception handler boundary in streamlit_app.py logging to error.log.
- Rotating file log handler in app data directory logging to app.log.

---

[0.4.0] – 2026-06-23
Changed
- RAG indexing refactored to use 2000-character sliding window chunks with 200-character overlap.
- Profiling upgraded to retrieve top-20 most relevant personality chunks for analysis.
- Audio voice transcription configured to auto-detect and transcribe English and Urdu.
Added
- Unified LLM interface supporting both local Ollama and Google Gemini.
- Embedding dimension consistency check and auto-recreation on startup.
- API retry wrapper with exponential backoff.

---

[0.3.0] – 2026-06-23
Changed
- Local storage relocated to %LOCALAPPDATA%/InstaSync on Windows.
- Storage Manager refactored to handle only text chats and audio files (images purged).
- Folder names sanitized against Windows invalid directory character rules.
Added
- Pre-flight filesystem and disk-space checks.
- Windows long-path prefix support.

---

[0.2.0] – 2026-06-23
Added
- Ollama local model auto-detection and priority ranking.
- Hybrid routing between Gemini (cloud) and Ollama (local).
- Mandatory privacy consent gate.
- Simple password gate.
Removed
- Image downloading and captioning.

---

[0.1.0] – 2026-06-23
Initial project version (prior to improvements)
