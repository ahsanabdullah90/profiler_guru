Version History

[0.9.9] – 2026-07-03
Added
- Sidebar navigation (`Sidebar.tsx`): Persistent 60px icon sidebar on left edge with Home, Import, Settings, Logout. Active state indicator with purple accent bar.
- Navigation store (`navigationStore.ts`): Tracks `activeSection` ('home' | 'import' | 'settings')
- Settings panel (`SettingsPanel.tsx`): Basic settings form for cloud provider, API key, Ollama model, deep scan toggle
- Import panel (`ImportPanel.tsx`): Data import form with folder path input and status feedback
Changed
- Header bars now use `bg-zinc-900` instead of invisible `bg-[rgba(10,10,12,0.2)]` — back buttons and exit chat buttons are now clearly visible
- Back/Exit buttons use `bg-primary/15 border-primary/30` for visible purple tint
- Ctrl+K search button repositioned next to sidebar
- Page layout updated: Sidebar added to left edge, content renders conditionally per navigation section
- All 82 tests pass, frontend builds clean

[0.9.8] – 2026-07-03
Added
- `src/utils/markdown.py`: Shared `parse_message_blocks()` utility (replaces 7 duplicated block-splitting patterns)
- `src/utils/markdown.py`: Shared `filter_month_files()` utility (replaces 3 duplicated month-filtering patterns)
- `get_contact_metadata()` method on MetricsEngine (fixes N+1 query in contacts_service)
- `frontend/src/lib/useDebounce.ts`: Shared `useDebouncedCallback` hook (replaces 3 duplicated implementations)
- `clearProfile` action to ragStore (replaces direct `setState()` from components)
- `fetchTasks()` call on ProgressPanel mount (tasks listed immediately if panel starts expanded)
- Logging to redis_client exception handlers for observability
Changed
- Backend performance: Moved datetime import out of inner loop, get_chat_paths out of per-message loop, backfill_existing_logs now batches commits, extracted shared _resolve_date_str(), cached tiktoken encoding + genai.Client, moved inline JSONResponse imports
- Backend code health: Deduplicated block-splitting in update_transcribed_message (7→1), replaced `__import__` hack, deprecated asyncio.get_event_loop() → get_running_loop(), broadcaster task now cancelled on shutdown
- Frontend performance: page.tsx now uses individual store selectors (was re-rendering entire tree on any change), derived arrays memoized with useMemo, audioBase memoized, keyboard listener stabilized with ref
- Frontend a11y: Added aria-labels to checkboxes, pagination, icon buttons. Fixed array index→composite key in chat history. Added htmlFor/id on select labels.
- Renamed `frontend/src/store/useTaskStore.ts` → `taskStore.ts` for consistent naming
Fixed
- Rate limiter no longer uses unbounded history dict (periodic eviction at 1000+ IPs)
- All 82 tests pass (was 52)

[0.9.7] – 2026-07-01
Removed
- Dead file `src/api/state.py` (comment-only stub, unused since v0.9.5)
- Dead file `frontend/src/store/useSyncStore.ts` (deprecated re-export stub)
- Unused `import os` from `main_api.py`
- Unused `from typing import List` from `api_settings.py`, `api_contacts.py`
- Unused `cache_get` import from `services/contacts_service.py`
- Unused `heartbeat_task` variable from `main_api.py`
Changed
- Removed stale entries from `tests/ISSUES_LOG.md` (WebSocket bug #1, Toast a11y #2 — fixed in P1)

[0.9.6] – 2026-06-30
Changed
- APP_PASSWORD now enforced as bcrypt at startup; plaintext rejected with clear error message
- /auth/login endpoint now rate-limited to 5 req/60s per IP
- SECRET_KEY is now required; removed `os.urandom(32).hex()` fallback
- `.env` updated with bcrypt APP_PASSWORD and SECRET_KEY
- `.env.example` updated with generation commands
- tests/conftest.py now sets bcrypt env vars before config import
Fixed
- 13 skipped API tests now run (APP_PASSWORD properly configured in test env)
- All 82 tests pass (was 69 with 13 skipped)
Removed
- Instagram Live Sync: Removed `instagram_sync.py`, `api_instagram.py`, and the `instagrapi` dependency. The app no longer performs live DM syncing from Instagram's API.
- Instagram API endpoints: Removed `/api/v1/instagram/status`, `/api/v1/instagram/login`, `/api/v1/instagram/2fa`, `/api/v1/instagram/sync/once`, `/api/v1/instagram/sync/toggle`.
- Instagram login/2FA UI: Simplified Header component to brand-only bar. Removed IG credential inputs, 2FA form, challenge URL display, and daemon sync toggle.
- `INSTAGRAM_PASSWORD` config variable and keyring storage.
- `last_user_activity` dead code from Config.
- `SYNC_INTERVAL` env variable (unused in code).
Changed
- `api_contacts.py` and `api_tasks.py` now use `MetricsEngine()` directly instead of accessing it via `sync_engine.metrics_engine`.
- `data_importer.py` no longer accepts `sync_engine` parameter. Cache invalidation after import uses `invalidate_contacts_cache()` directly.
- Status payload no longer includes `instagram_sync` field. Frontend status types updated accordingly.
- Page title updated to "Profile Guru — AI DM Intelligence".
Fixed
- Documentation audit: README.md, tests/README.md, LOGGING.md updated to match actual codebase state.

[0.9.4] – 2026-06-26
Added
- Google Gemini 1.5 Flash Cloud Audio ASR: Integrated high-accuracy cloud-based audio transcription via the `google-genai` SDK, preserving bilingual English/Urdu speech and optimizing local CPU/GPU resources, with a robust fallback to local `faster-whisper`.
- MediaProcessor automated tests (`tests/test_media_processor.py`) covering successful cloud ASR, Whisper fallback, and direct Whisper execution.
Fixed
- Frontend Workspace viewport overflow: Applied `min-h-0` to Column A, Column B, and the main rigid two-column flex container in `page.tsx`. This constrains column heights, prevents the browser from scrolling Column A on chat load, and restores the visibility and functionality of the "Exit Chat" button and monthly selector.
- CORS preflight OPTIONS requests: Exempted `OPTIONS` requests from the JWT authentication middleware to prevent browser preflight blocks (returning 401 Unauthorized) and added unit tests covering preflight requests.
- Test suite fixes: Corrected `test_llm_dispatcher_missing_key_fallback` in `test_personality_gui.py` to assert that `LLMDispatchError` is raised when the Cloud API Key is missing, ensuring the full test suite passes.

[0.9.3] – 2026-06-26
Added
- Sequential Ingestion & Humanized Sync: Replaced concurrent fetching with human-paced sequential synchronization, incorporating randomized delays between threads (2-5s) and messages (0.5-1.5s).
- Circadian Sync Interval: Implemented Gaussian-jittered sync interval calculations (daytime ~5m, nighttime ~15m) and nighttime sleep skip simulation (10% chance) to evade anti-bot rate limits.
- Stable Vector Indexing: Appended invisible HTML comments `<!-- chunk_id: ... -->` to saved messages and refactored RAGEngine indexing to parse and use them as stable ChromaDB document IDs.
- Non-Blocking Startup Vacuum: Implemented a delayed background vacuum task (`vacuum_orphaned_vectors()`) triggered 60s after startup to clean orphaned vector records without blocking Streamlit boot.
- Checkpoint Challenge UI: Created an interactive suspicious login warning box in the sidebar with a direct clickable link to the verification URL and a Retry Login trigger.
- Process-Wide Import Lock: Introduced a process-wide `IMPORT_LOCK` singleton to secure background imports and UI operations against rerun issues.
- PDF Generation XML Safety: Refactored markdown-to-pdf parsing to XML-escape raw text before markdown replacements, ensuring operators like `<` or `>` do not crash ReportLab.
- Complete Test Coverage: Added 8 new automated unit tests verifying sequential sync, stable indexing, PDF operator safety, vacuum cleaning, and stop event aborts (all 45 tests passing).

[0.9.2] – 2026-06-25
Fixed
- Resolved a critical NameError: name 'Path' is not defined in streamlit_app.py by importing Path from pathlib, fixing the crash that occurs when selecting a contact and restoring the Personality Assessment, Connection Analysis, and Ask AI (RAG) tabs.
- Fixed an issue in settings_manager.py where exports/settings.json would override the .env API key with an empty string, by automatically importing and persisting the .env key on load if the JSON configuration's key is empty.

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
- Local storage relocated to %LOCALAPPDATA%/Profile_Guru on Windows.
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
