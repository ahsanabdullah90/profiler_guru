# Changelog

All notable changes to the Profile Guru project are documented in this file.

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
