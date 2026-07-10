# Changelog

All notable changes to the Profile Guru project are documented in this file.

---

## [1.3.0] – 2026-07-10 — Repository Audit Fixes & Test Coverage

### Added
- **Vitest Test Suite:** Introduced frontend unit testing with Vitest (jsdom environment). Initial coverage targets `src/lib/apiConfig.ts`, `src/store/api.ts`, `src/store/authStore.ts`, and `src/store/contactsStore.ts`. Run via `npm test`.
- **`src/lib/apiConfig.ts`:** New zero-dependency module exporting `API_PORT`, `API_VERSION`, `CONTACTS_FETCH_TIMEOUT`, `getApiBase()`, `fetchWithTimeout()`, and a token/auth-expiry bridge pattern used to break circular store imports.
- **`SECURITY.md` — Known Accepted Risks:** Documented the `postcss < 8.5.10` CVE (CWE-79, CVSS 6.1) bundled inside `next@16.2.9` as an accepted risk. Cannot be patched without a breaking downgrade incompatible with React 19. Review scheduled for 2026-10-10.

### Fixed
- **Circular Store Dependencies (3 cycles):** Resolved all three import cycles detected by `madge`:
  - `api.ts ↔ authStore.ts` — `api.ts` now reads the JWT via `getAuthToken()` registered by `authStore` at init time.
  - `api.ts ↔ statusStore.ts` — `statusStore` now imports `getApiBase` and `fetchWithTimeout` from `apiConfig` instead of `api.ts`.
  - `contactsStore.ts ↔ ragStore.ts` — `ragStore.fetchProfile()` now accepts an optional `AbortSignal` parameter supplied by `contactsStore`, removing the need to import `contactsStore` from within `ragStore`.
- **Magic Literals:** Replaced hardcoded `60000` in `contactsStore.fetchContacts` with the named constant `CONTACTS_FETCH_TIMEOUT` from `apiConfig`.
- **Extraneous node_modules:** Cleaned 5 orphaned `@emnapi/*` / `@napi-rs/*` packages via `npm prune`.

### Security
- **[ACCEPTED]** `postcss < 8.5.10` XSS (CWE-79, CVSS 6.1) — bundled in `next@16.2.9`. Not exploitable in this codebase. See [SECURITY.md](../SECURITY.md) for full rationale.

---

## [1.2.1] – 2026-07-10 — RAG, Schema Migration, and Workspace Navigation Fixes

### Added
- **RAG Indexing Requirement Detection:** Updates the backend to verify if any imported contact has unindexed messages in ChromaDB when the reindexing task is idle. If found, it reports a `needs_indexing` state.
- **RAG Status Bar UI indicators:** Visualized the `needs_indexing` RAG status on the frontend footer with an amber status dot and an `Index Required` label. The "Reindex RAG" button now pulsates with an amber theme to prompt the user to start indexing.
- **Self-Healing UUID Backfill:** Added a database startup hook to automatically generate and assign UUIDs (`client_id`) for any contacts in `contact_metadata` that do not have one, resolving URL path validation errors on contacts with special characters.
- **Authenticated PDF Downloads:** Supported validating JWT authorization tokens passed as URL query parameters (`?token=...`) in `get_current_user`, resolving `401 Unauthorized` errors when triggering downloads via direct browser window navigation (`window.open`).

### Fixed
- **Older SQLite Schema Migrations:** Expanded the self-healing DB migrations in `metrics_engine.py` to add all newer columns (`scores`, `classification`, `pipeline_mode`, `total_steps`, `model_provider`, `model_name`, `summary`) to the `assessment_history` table if missing, preventing SQL error crashes (`no such column: scores`).
- **Workspace Exit & Selection Loop:** Fixed `setSelectedContact` in `contactsStore.ts` to set the active selection to `contactId` (instead of display name) and added a null guard to prevent evaluating the search if `contact` is null, fixing card highlighting, API query routing, and workspace exit lockups.
- **Dynamic Display Name Resolution:** Changed `Inspector.tsx`, `AIHubRAGChat.tsx`, and `AIHubAssessment.tsx` to lookup and display friendly display names dynamically in the views.
- **Workspace Type Definitions:** Used the proper `Contact` interface in `Workspace.tsx`'s `ContactCard` props to resolve property compilation errors.

---

## [1.2.0] – 2026-07-10 — Data Sources Dashboard Refactor
### Changed
- **ImportPanel Two-Column Layout:** Redesigned the Data Sources dashboard from a single-column stacked layout to a responsive two-column grid (`grid-cols-1 lg:grid-cols-2`). Left column is WhatsApp (green accent `#25D366`), right column is Instagram (pink accent `#E1306C`).
- **Platform-Specific UI:** Each column has a distinct colored header bar with platform icon, stats grid, and action buttons. WhatsApp column shows bridge status, message/contact counts, and migrate/reconnect buttons. Instagram column shows drag-and-drop zone, path input, and import button.
- **Full-Width Info Sections:** "What goes here" and "What happens after import" sections moved below both columns as shared help content, rewritten to describe both platforms.

---

## [1.1.0] – 2026-07-10 — Sprint 6-8: WhatsApp Bridge, Compliance, Feature Flags
### Added
- **WhatsApp Bridge Integration (Sprint 6):** Live message ingestion via `listener.js` → `POST /api/v1/whatsapp/ingest`. Auto-merge by phone number, fuzzy name-matching (threshold 0.72) with pending merge suggestions. XML migration endpoint for historical chat exports.
- **Contact Merge System (Sprint 6):** `merge_contacts()` cascade in `contact_merge.py` — merges markdown logs (dedup by chunk_id), relocates audio files, reassigns 9 SQLite tables, deletes ChromaDB vectors, invalidates Redis cache. Three-layer merge: auto-merge by phone, name-similarity suggestion, manual merge via UI.
- **Platform Tracking (Sprint 6):** `contact_platforms` table tracks which platforms (instagram/whatsapp) each contact has messages from. `pending_merges` table stores fuzzy match suggestions. `PlatformBadge.tsx` component displays platform pills on contact cards.
- **Encryption at Rest (Sprint 7):** `encryption.py` implements Fernet (AES-128-CBC) with OS keyring integration. Clinical notes automatically encrypted before SQLite write, decrypted on read. Fail-open behavior if keyring unavailable.
- **Right-to-Be-Forgotten (Sprint 7):** `purge_patient()` cascade in `metrics_engine.py` — deletes across 6 SQLite tables, chat files, audio files, profile photos, ChromaDB vectors. Writes audit tombstone to `purged_patients` table. `DELETE /clinical/{patient_id}` endpoint.
- **Feature Flags (Sprint 8):** `feature_gate.py` implements free/pro tier gating. Free tier features (clinical_instruments, trait_frameworks, unlimited_patients, whatsapp_import, audio_upload) enabled. Pro features (report_library, framework_expansion_packs, cloud_sync) disabled. `GET /settings/features` endpoint.
- **Frontend Feature Gate (Sprint 8):** `FeatureGate.tsx` React context + `TierBadge` component. Settings → Plan tab displays current tier and feature availability.

### Changed
- **Unified Client Roster:** Replaced separate IG/WhatsApp dashboards with single client list + platform filter chips (`[All][Instagram][WhatsApp]`). Contact merge supports 3 layers: auto-merge by phone, name-similarity suggestion, manual merge tool.
- **Startup Optimization:** Deferred `rag_engine` initialization from synchronous lifespan to background task. Health endpoint now responds in ~0.1s instead of ~25s. rag_engine still initializes in background ~3s after server starts.

### Fixed
- **Launcher Startup Failure:** `run.bat` now verifies venv has required dependencies (fastapi import check) before using it. Falls back to system Python if venv is missing packages.
- **Backend Startup Blocking:** Moved rag_engine init to async background task in `main_api.py` lifespan. Health endpoint responds immediately, no functionality lost.

---

## [1.0.1] – 2026-07-10 — Launcher Fix
### Fixed
- **Launcher Startup Failure (`run.bat`):** Replaced `%ERRORLEVEL%` environment variable references inside parenthesized blocks with `if errorlevel 1` checks to prevent pre-execution expansion failures.
- **Dependencies Backfill:** Verified and installed all missing FastAPI/Uvicorn python dependencies inside `.venv`.

---

## [1.0.0] – 2026-07-03 — UI/UX Modernization GA
### Added
- **Onboarding Tour Overlay:** Introduces a first-run wizard highlighting panels and workspace divisions, persisted in localStorage.
- **Keyboard Shortcuts Dialog:** Interactive cheatsheet mapping all power-user keys, triggered via `?` or the User Menu.
- **Zustand UI Store:** Centralizes application theme state, inspector dimensions, onboarding progress, and modal flags.

### Changed
- **Token Migration Complete (GA):** Entire Next.js layout migrated to semantic CSS variable tokens. All legacy Tailwind hardcoded colors removed.
- **A11y Global Modals:** Replaced div overlays with accessible dialog structures containing Escape listener hooks and proper aria focus management.

### Fixed
- **Contrast Ratios:** Verified brand teal (`#1F5F6E`) and canvas backgrounds yield a passing 6.6:1 contrast ratio in Light mode.

---

## [0.11.0] – 2026-07-03 — UI Rebuilds & Accessibility sprin
### Added
- **UI Primitives:** Introduced `<Skeleton>` loaders, `<EmptyState>` cards, and Recharts `<ChartFrame>` wrapper supporting CSV data exports.
- **Accessibility Checks:** Added `eslint-plugin-jsx-a11y` rules to CI, resolving form labels, button types, fieldsets, and media caption tracks.

### Changed
- **StatusBar Rebuild:** Redesigned Status Bar to a token-driven, 28px collapsed / 200px expanded bar featuring active background task trackers.
- **Settings Rebuild:** Segmented configuration fields into clear navigation blocks (Data / Models / Reports).

---

## [0.10.0] – 2026-07-03 — UI/UX Modernization & Inspector
### Added
- **Inspector Pane:** Resizable right-rail pane containing contact tags, flags, and a notes editor with a 1-second auto-save debounce loop.
- **Inspector Store:** Programmed a secure, JSON-backed thread-safe store (`inspector_store.py`) with atomic temp-writes and backups.
- **Navigation Redesign:** Replaced left sidebar navigation with a persistent header User Menu.

---

## [0.9.6] – 2026-06-30 — Security Hardening
### Changed
- **Bcrypt Passwords:** Backend requires Bcrypt-hashed configurations (`APP_PASSWORD`) at startup and rejects plaintext.
- **Login Rate Limiting:** Enforces `RateLimiter` dependency on login routes (max 5 requests per 60 seconds).
- **Mandatory Secrets:** Disables automatic key generation fallback; `SECRET_KEY` is now mandatory in `.env`.

### Removed
- **Instagram Live sync:** Purged legacy live syncing engines (`instagram_sync.py`) and API controllers (`api_instagram.py`) due to anti-bot rate blocks. Project is now fully **Import-Only**.

---

## [0.9.4] – 2026-06-26 — Cloud ASR Integration
### Added
- **Google Gemini ASR:** Integrated cloud-based audio transcription using the `google-genai` SDK, offering bilingual Urdu/English speech support and falling back to local Whisper.

---

## [0.9.3] – 2026-06-26 — Ingestion Jitter & Stable Indexing
### Added
- **Stable Vector Chunks:** Appends unique ID HTML comments (`<!-- chunk_id: ... -->`) to messages, ensuring ChromaDB aligns vector updates exactly.
- **Sequential Imports:** Implemented randomized delays between messages (0.5s-1.5s) to humanize import processing.
- **Delayed Startup Vacuum:** Implemented a background vacuum task that clears orphaned vector nodes 60 seconds after server launch.
