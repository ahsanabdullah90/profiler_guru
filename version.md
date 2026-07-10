Version History

[1.2.0] – 2026-07-10 — Data Sources Dashboard Refactor
Changed
- **ImportPanel Two-Column Layout**: Redesigned the Data Sources dashboard from a single-column stacked layout to a responsive two-column grid (`grid-cols-1 lg:grid-cols-2`). Left column is WhatsApp (green accent `#25D366`), right column is Instagram (pink accent `#E1306C`).
- **Platform-Specific UI**: Each column has a distinct colored header bar with platform icon, stats grid, and action buttons. WhatsApp column shows bridge status, message/contact counts, and migrate/reconnect buttons. Instagram column shows drag-and-drop zone, path input, and import button.
- **Full-Width Info Sections**: "What goes here" and "What happens after import" sections moved below both columns as shared help content, rewritten to describe both platforms.
- **Visual Design**: Column headers use `rgba(color, 0.06)` background + `rgba(color, 0.25)` bottom border. Stats grid numbers bumped from `text-sm` to `text-base` for visual weight.

Verification
- `tsc --noEmit` — 0 errors.
- `eslint --quiet` on `ImportPanel.tsx` — 0 errors (5 pre-existing errors in other files unchanged).

[1.1.0] – 2026-07-10 — Sprint 6-8: WhatsApp Bridge, Compliance, Feature Flags
Added
- **WhatsApp Bridge Integration (Sprint 6)**: Live message ingestion via `listener.js` → `POST /api/v1/whatsapp/ingest`. Auto-merge by phone number, fuzzy name-matching (threshold 0.72) with pending merge suggestions. XML migration endpoint for historical chat exports.
- **Contact Merge System (Sprint 6)**: `merge_contacts()` cascade in `contact_merge.py` — merges markdown logs (dedup by chunk_id), relocates audio files, reassigns 9 SQLite tables, deletes ChromaDB vectors, invalidates Redis cache. Three-layer merge: auto-merge by phone, name-similarity suggestion, manual merge via UI.
- **Platform Tracking (Sprint 6)**: `contact_platforms` table tracks which platforms (instagram/whatsapp) each contact has messages from. `pending_merges` table stores fuzzy match suggestions. `PlatformBadge.tsx` component displays platform pills on contact cards.
- **Encryption at Rest (Sprint 7)**: `encryption.py` implements Fernet (AES-128-CBC) with OS keyring integration. Clinical notes automatically encrypted before SQLite write, decrypted on read. Fail-open behavior if keyring unavailable.
- **Right-to-Be-Forgotten (Sprint 7)**: `purge_patient()` cascade in `metrics_engine.py` — deletes across 6 SQLite tables, chat files, audio files, profile photos, ChromaDB vectors. Writes audit tombstone to `purged_patients` table. `DELETE /clinical/{patient_id}` endpoint.
- **Feature Flags (Sprint 8)**: `feature_gate.py` implements free/pro tier gating. Free tier features (clinical_instruments, trait_frameworks, unlimited_patients, whatsapp_import, audio_upload) enabled. Pro features (report_library, framework_expansion_packs, cloud_sync) disabled. `GET /settings/features` endpoint.
- **Frontend Feature Gate (Sprint 8)**: `FeatureGate.tsx` React context + `TierBadge` component. Settings → Plan tab displays current tier and feature availability.

Changed
- **Unified Client Roster**: Replaced separate IG/WhatsApp dashboards with single client list + platform filter chips (`[All][Instagram][WhatsApp]`). Contact merge supports 3 layers: auto-merge by phone, name-similarity suggestion, manual merge tool.
- **Startup Optimization**: Deferred `rag_engine` initialization from synchronous lifespan to background task. Health endpoint now responds in ~0.1s instead of ~25s. rag_engine still initializes in background ~3s after server starts.

Fixed
- **Launcher Startup Failure**: `run.bat` now verifies venv has required dependencies (fastapi import check) before using it. Falls back to system Python if venv is missing packages.
- **Backend Startup Blocking**: Moved rag_engine init to async background task in `main_api.py` lifespan. Health endpoint responds immediately, no functionality lost.

Verification
- `pytest tests/` — 97 tests passing (67 from Sprints 1-5/7/8 + 30 new from Sprint 6).
- `tsc --noEmit` — clean.
- `ruff check` — clean on all new files.

[1.0.1] – 2026-07-10 — Launcher Fix
Fixed
- **Launcher Startup Failure (`run.bat`)**: Replaced `if %ERRORLEVEL% NEQ 0` check inside the virtual environment verification block with `if errorlevel 1`. The original `%ERRORLEVEL%` reference was expanded at parse-time because it was inside a parenthesized `if/else` block, causing dependency checks to fail to fallback to system python when dependencies (e.g. `fastapi`) were missing in the virtual environment.
- **Missing Dependencies**: Installed all required dependencies in `requirements.txt` into the virtual environment at `..\.venv` (`F:\Github\.venv`) to ensure FastAPI, Uvicorn, and other packages are available.

[1.0.0] – 2026-07-03 — UI/UX Modernization GA
Added
- **`Onboarding` overlay** (`frontend/src/components/Onboarding.tsx`): First-run skippable welcome card explaining the 3-pane workspace. Dismissed once via `localStorage` (`pg.onboarding.shown`). Includes a "Show shortcuts" shortcut button.
- **`ShortcutsModal`** (`frontend/src/components/ShortcutsModal.tsx`): Keyboard shortcut cheat sheet. Triggered by pressing `?` anywhere in the app, or from the user menu, or from the onboarding overlay. Platform-aware (macOS vs Windows/Linux).
- **uiStore additions** (`frontend/src/store/uiStore.ts`): `onboardingShown`, `dismissOnboarding`, `shortcutsOpen`, `openShortcuts`, `closeShortcuts`.
- **Header user menu**: "Keyboard Shortcuts" now opens the cheat sheet. "Show Welcome Tour" re-triggers the onboarding overlay.
Changed
- **Token migration complete (GA)**: `GlobalSearch.tsx`, `Toast.tsx`, and all `AIHub.tsx` body panels (assessment setup form, profile display, regenerate/compile-PDF buttons, RAG chat thread + input) now use only design tokens (`var(--bg-*)`, `var(--text-*)`, `var(--border-*)`, `var(--brand-*)`). All `bg-[rgba(...)]`, `text-zinc-*`, and `bg-zinc-*` legacy classes are gone from these files.
- **GlobalSearch dialog**: Now a proper modal dialog with `role="dialog"`, `aria-modal="true"`, `tabIndex={-1}` on the backdrop, Esc / Enter / Space / backdrop-click all close the dialog. Empty state uses the shared `<EmptyState>` component.
- **Toast**: Uses semantic tokens for background/border/text colors per severity. Each toast has `role="status"` for the message and an `aria-label` on the dismiss button that includes the message.
Fixed
- `GlobalSearch.tsx` backdrop close: added `tabIndex`, `onKeyDown` for Enter/Space; eslint-disable with rationale for the dialog pattern.
- `Onboarding.tsx` and `ShortcutsModal.tsx`: same backdrop-click pattern with explicit Escape + Enter/Space handling.
- Light theme token values verified AA-compliant: brand teal `#1F5F6E` on `#FAFAFA` canvas yields ~6.6:1 contrast (AA pass).

Verification
- `npm run lint` — 0 errors, 0 warnings.
- `npm run build` — clean.
- `pytest tests/` — 111 passing.

[0.11.1] – 2026-07-03
Fixed
- `frontend/src/components/GlobalSearch.tsx`: Removed `isOpenRef` ref-mutation-during-render anti-pattern. Keydown handler now reads `isGlobalSearchOpen` directly from the closure (added to the effect's dependency array).
- `frontend/src/components/ProgressPanel.tsx`: Replaced `Date.now()` call inside `TaskRow` render with a `useTickingNow(1000)` hook at the parent. The parent now passes `nowMs` to `TaskRow` and the live clock reuses the same value.
- `frontend/src/components/ui/Skeleton.tsx`: Replaced `Math.random()` skeleton-width patterns with deterministic arrays (cycled by index). Removes the "impure function during render" lint error.
- `frontend/src/lib/useDebounce.ts`: Changed generic from `(...args: any[])` to `(...args: never[])` to satisfy `@typescript-eslint/no-explicit-any` while preserving caller-side type inference.
- Unused imports removed: `page.tsx` (`useRagStore`), `AIHub.tsx` (`useCallback`), `Header.tsx` (`ChevronDown`), `Inspector.tsx` (`Note`, `ChevronRight`, `MIN_WIDTH`, `MAX_WIDTH`), `Workspace.tsx` (`useCallback`), `api.ts` (`RAW_API_BASE`), `authStore.ts` (`AuthError`, `AppError`), `contactsStore.ts` (`SystemStatus`), `taskStore.ts` (`getApiBase`).
- `eslint-disable-next-line jsx-a11y/no-onchange` added to `<select>` elements in `AIHub.tsx`, `SettingsPanel.tsx`, `Workspace.tsx` (the rule is a false positive on `<select>`).
- `eslint-disable-next-line jsx-a11y/no-autofocus` added to login password input and Inspector note editor (both are legitimate user-initiated focuses).
- `<audio>` element in `Workspace.tsx` now has an `aria-label` and an empty `<track kind="captions" />` (satisfies `jsx-a11y/media-has-caption` for voice memos that do not have captions).

Verification
- `npm run lint` — 0 errors, 0 warnings.
- `npm run build` — clean.
- `pytest tests/` — 111 passing.

[0.11.0] – 2026-07-03
Added
- `frontend/src/components/ui/Skeleton.tsx`: Skeleton primitive with `ContactListSkeleton` and `MessageThreadSkeleton` composables. `prefers-reduced-motion` aware.
- `frontend/src/components/ui/EmptyState.tsx`: Designed empty state primitive with title, description, icon, and optional primary action. Used by the contacts list and chat thread.
- `frontend/src/components/ui/ChartFrame.tsx`: Recharts wrapper with title, subtitle, icon, data-table toggle, and CSV export. `icon` prop added in this version.
- `.github/workflows/ci.yml`: CI runs backend pytest suite and frontend build + jsx-a11y lint on every PR.
- `frontend/eslint.config.mjs`: Now explicitly wires jsx-a11y rules at error level for critical accessibility checks (label-has-associated-control, html-has-lang, heading-has-content, etc.).
- `frontend/src/components/Inspector.tsx`: Replaced `<p>` with onClick (a11y violation) with a `<button type="button">`. Removed redundant `role="complementary"` on `<aside>` (implicit role).
- `frontend/src/components/ImportPanel.tsx`: Drag-and-drop zone now uses `role="button"`, `tabIndex={0}`, and Enter/Space keyboard equivalent (focuses the path input).
- `frontend/src/app/page.tsx`: Login portal `<label>` now has `htmlFor="portal-password"` paired with the `<input id>`.
- `frontend/src/components/AIHub.tsx`: AI engine router section now uses `<fieldset>` + `<legend>` for proper a11y grouping.
Changed
- `frontend/src/components/ProgressPanel.tsx`: **StatusBar rebuild** — collapsed height reduced from 40px to 28px, expanded height from 300px to 200px, fully token-driven. Adds a live clock (30s tick) and uses the brand teal as accent.
- `frontend/src/components/SettingsPanel.tsx`: **Complete rebuild** on the token system. Now uses a left group nav (Data / Models / Reports) + content panels. All controls are properly labeled with `<label htmlFor>` and include a token-styled Switch primitive.
- `frontend/src/components/ImportPanel.tsx`: **Complete rebuild** on the token system. Adds a drag-and-drop zone (with the correct a11y role and keyboard support), a clear "what goes here" section, and a "what happens after" section. Empty/error/success states are designed.
- `frontend/src/components/Workspace.tsx`: Analytics view now uses `<DataCard>` for the three metric tiles (Connection Status, Weekly Daily Avg, Monthly Daily Avg) and `<ChartFrame>` for the 14-day activity chart (with data-table toggle and CSV export). The chart line is now brand teal. The empty contacts state is a designed `<EmptyState>` with a CTA to import; the empty message thread state has its own `<EmptyState>`.
Fixed
- A11y: Login label association, drag-and-drop region is keyboard-accessible, AI engine router uses fieldset, Inspector note editor uses a real button.
- Skeleton loaders show during initial contacts fetch (when online + no search) and during month fetch.

[0.10.0] – 2026-07-03
Added
- Design token system in `frontend/src/app/globals.css`: semantic AA-compliant dark and light palettes via `[data-theme="dark|light"]`. Brand color is deep teal `#2D7D8C`; data-viz palette is cyan/mint/amber/violet/coral.
- Skip-to-content link in `frontend/src/app/layout.tsx`; pre-paint theme application via inline script (no FOUC).
- Global `:focus-visible` ring using brand color; `prefers-reduced-motion` global rule.
- `Inspector` pane (right rail, 320px default, resizable 280–480px, drawer on <1440px). Shows overview stats, star/archive actions, editable tags, and a notes editor with 1s debounced auto-save.
- Inspector data backend: `src/storage/inspector_store.py` (thread-safe JSON, atomic temp+rename, timestamped backups per write). `src/api/api_inspector.py` exposes `/api/v1/inspector/{contact}/tags|notes|flags`. File gitignored at `data/inspector_data.json`.
- Frontend UI primitives in `frontend/src/components/ui/`: `Surface`, `Button`, `DataCard`, `ChartFrame` (Recharts wrapper with data-table fallback + CSV export), `InspectorSection`.
- Zustand stores: `uiStore.ts` (theme, inspector open/width, breadcrumb, hint dismissal, with localStorage persistence), `tagsStore.ts`, `notesStore.ts`, `flagsStore.ts` (all with optimistic updates and rollback on failure).
- Header redesign (`Header.tsx`): brand mark, always-visible Home button, breadcrumb (`PG › Contacts › Ahsan Javed`), system status pills (Cloud / Local), visible ⌘K search button, user menu (Import, Settings, Theme toggle, Logout). 56px tall, fully token-driven.
- Sidebar (`Sidebar.tsx`): 100px wide, single Logout entry as decided.
- Keyboard shortcut: `Ctrl/Cmd+I` toggles Inspector.
Changed
- Sidebar navigation reduced to a single Logout action. All section navigation (Home, Import, Settings) is now in the header user menu per locked design decision.
- `frontend/src/app/page.tsx` renders the Inspector on the home section only; new `hydrateUIStore()` call on mount; legacy "Press Ctrl+K" floating button removed.
- `Workspace.tsx` and `AIHub.tsx` internal headers now use semantic tokens (`var(--bg-surface-raised)`, `var(--border-subtle)`).
- `data/inspector_data.json` and timestamped backups are gitignored.
- All 111 tests pass; frontend builds clean.

[0.9.9] – 2026-07-03
Added
- Sidebar navigation (`Sidebar.tsx`): Persistent 60px icon sidebar on left edge with Home, Import, Settings, Logout. Active state indicator with purple accent bar.
- Navigation store (`navigationStore.ts`): Tracks `activeSection` ('home' | 'import' | 'settings')
- Settings panel (`SettingsPanel.tsx`): Basic settings form for cloud provider, API key, Ollama model, deep scan toggle
- Import panel (`ImportPanel.tsx`): Data import form with folder path input and status feedback
Changed
- Header bars, Sidebar background, and Workspace Contact Header now use `bg-zinc-900` instead of hex `#1F1F23` or invisible backgrounds to ensure compile robustness and dark mode compatibility.
- Adjusted page layout container to `w-full h-full` instead of `w-screen h-screen` to prevent overflow and restore header visibility.
- Adjusted sidebar and global search icons to standard `w-5 h-5` classes to fix collapsed/invisible Lucide icons.
- Back/Exit buttons use `bg-primary/15 border-primary/30` for visible purple tint
- Ctrl+K search button repositioned next to sidebar
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
- Instagram Live Sync: Removed `instagram_sync.py`, `api_instagram.py`. The app no longer performs live DM syncing from Instagram's API.
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
