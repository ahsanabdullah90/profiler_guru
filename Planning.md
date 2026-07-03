# Planning.md — Profile Guru Development Roadmap

**Last Updated:** 2026-07-03
**Current Version:** 0.9.8 (code quality sprint complete)
**Test Status:** 82 tests passing, 64% coverage

---

## 1. Project Status Snapshot

### ✅ Completed: Completed: Instagram Live Sync Removal (v0.9.5)
**Removed:**
- `src/engine/instagram_sync.py` (575 lines) — Live sync engine, InstagramSync, SyncManager
- `src/api/api_instagram.py` (135 lines) — /instagram endpoints (login, 2fa, status, sync/once, sync/toggle)
- `tests/test_sync.py` (132 lines) — Sync test suite
- `instagrapi==2.16.24` from requirements.txt
- `INSTAGRAM_PASSWORD`, `SYNC_INTERVAL` from .env.example
- Frontend: Header IG login/2FA/sync UI, useSyncStore instagram_sync actions/state, ProgressPanel sync indicator, StatusService IG passthrough, WS instagram_sync type
- Legacy redirect map entries for /api/instagram/*

**Decoupled:**
- `api_contacts.py` & `api_tasks.py` now use `MetricsEngine()` directly (singleton)
- `data_importer.py` no longer accepts `sync_engine`; cache invalidation via `invalidate_contacts_cache()`
- `config.py`: removed `INSTAGRAM_PASSWORD`, `last_user_activity` (dead code)
- `state.py`: deleted (was already gutted to comment-only in v0.9.5)

**Docs Updated:**
- `README.md` — removed sync features, updated structure, tech stack, data flows
- `tests/README.md` — added 7 missing test files, removed IG mocking
- `version.md` — added v0.9.5 entry
- `LOGGING.md` — removed phantom `error.log`
- `tests/ISSUES_LOG.md` — updated issue statuses, added architectural issues

**Verified:** 52 tests pass, zero remaining references to instagram_sync/api_instagram/instagrapi

### ✅ Completed: Code Quality Sprint — Phase 1 (v0.9.7)
**Cleanup:**
- Deleted dead file `src/api/state.py` (comment-only stub, unused since v0.9.5)
- Deleted dead file `frontend/src/store/useSyncStore.ts` (deprecated stub, already split into separate stores)
- Removed unused `import os` from `main_api.py`
- Removed unused `from typing import List` from `api_settings.py`, `api_contacts.py`
- Removed unused `cache_get` import from `services/contacts_service.py`
- Removed unused `heartbeat_task` variable from `main_api.py:362`
- Removed stale entries from `tests/ISSUES_LOG.md` (WebSocket bug #1, Toast a11y #2 — both fixed in P1)

**Docs Updated:**
- `Planning.md` — added v0.9.7 entry
- `tests/ISSUES_LOG.md` — marked P1-fixed issues as resolved, removed stale open items

### ✅ Completed: Code Quality Sprint — Phases 2-5 (v0.9.8)
**Backend Performance:**
- Moved `from datetime import datetime` out of inner loop in data_importer
- Moved `get_chat_paths` out of per-message loop (was called per msg, now per chat)
- `backfill_existing_logs` now batches via `increment_messages_batch` instead of per-message commits
- Extracted shared `_resolve_date_str()` — deduplicated 3 copies
- Cached tiktoken encoding object, `genai.Client`, moved inline `JSONResponse` imports
- Replaced `__import__` hack with normal import; added cleanup to `RateLimiter.history`

**Backend Code Health:**
- Created `src/utils/markdown.py` with `parse_message_blocks()` + `filter_month_files()`
- Deduplicated block-splitting across 7 locations; deduplicated month filtering across 3 locations
- Added `get_contact_metadata()` to MetricsEngine (fixes N+1 in contacts_service)
- Fixed deprecated `asyncio.get_event_loop()` → `get_running_loop()`
- Added logging to redis_client exception handlers
- Stored `system_status_broadcaster` task ref, cancel on shutdown

**Frontend Performance:**
- Fixed full-store subscription in `page.tsx` (was re-rendering entire tree on any store change)
- Memoized derived arrays (`runningTasks`/`recentTasks`), `audioBase`, stabilized keyboard listener
- Created shared `useDebouncedCallback` hook, replaced 3 duplicated debounce implementations
- Added `clearProfile` action to ragStore, removed direct `setState()` from components

**Frontend UX & Accessibility:**
- Added `aria-label` to icon-only buttons, checkboxes, pagination buttons
- Fixed array index → composite key in AIHub chat history
- Added `htmlFor`/`id` associations on select labels
- Added `fetchTasks()` on ProgressPanel mount
- Renamed `useTaskStore.ts` → `taskStore.ts` for consistent naming

**Docs Updated:**
- `Planning.md` — added v0.9.8 entry
- `version.md` — added v0.9.6 (P0 security), v0.9.7 (Phase 1), v0.9.8 (Phases 2-5)
- `tests/README.md` — noted conftest.py bcrypt env setup

**Verified:** 82 tests pass, frontend builds clean, lint passes.

---

## 2. Remaining Work — Prioritized

### P0: Critical Security (Must Fix Before Production)

| ID | Task | Files | Effort | Status |
|---|---|---|---|---|
| P0-1 | **Enforce bcrypt APP_PASSWORD** — reject plaintext at startup; remove fallback comparison | `src/api/api_auth.py`, `src/utils/config.py`, `.env.example` | 2h | ✅ |
| P0-2 | **Add rate limiting to /auth/login** — apply `RateLimiter` dependency | `src/api/api_auth.py`, `tests/conftest.py` | 1h | ✅ |
| P0-3 | **Fail fast if SECRET_KEY missing** — remove `os.urandom(32).hex()` fallback | `src/utils/config.py`, `.env`, `.env.example` | 30m | ✅ |
| P0-4 | **Rotate leaked GOOGLE_API_KEY** — user action required | `.env` (local) | — | ⬜ |

---

### P1: High-Priority Bug Fixes (Current Sprint)

| ID | Task | Files | Effort | Status |
|---|---|---|---|---|
| P1-1 | **WebSocket heartbeat-reconnect bug** — `resetHeartbeatWatchdog` calls `this.close()` which sets `destroyed=true` and blocks `scheduleReconnect`. Change to `this.ws?.close()` so `ws.onclose` triggers reconnection. | `frontend/src/lib/ws.ts:193` | 15m | ✅ |
| P1-2 | **tsconfig.json paths alias** — key is `"import-alias @/*"` (literal), should be `"@/*"` | `frontend/tsconfig.json:22` | 5m | ✅ |
| P1-3 | **Toast accessibility** — add `role="alert" aria-live="assertive"` to container; `aria-label="Dismiss"` to close button | `frontend/src/components/Toast.tsx:40,57` | 15m | ✅ |
| P1-4 | **Remove unused Python deps** — `sentencepiece`, `python-multipart` (keep `httpx`, `websockets` as transitive) | `requirements.txt` | 5m | ✅ |
| P1-5 | **Remove unused JS deps** — `@tanstack/react-query`, `framer-motion` | `frontend/package.json` | 5m | ✅ |
| P1-6 | **Rename test_broken.py → test_edge_cases.py** — update `tests/README.md:40` | `tests/test_broken.py`, `tests/README.md` | 10m | ✅ |

**Total P1 Effort:** ~55 minutes

---

### P2: Medium Priority (Next Sprint)

| ID | Task | Files | Effort | Status |
|---|---|---|---|---|
| P2-1 | **Add test coverage for untested modules** — `redis_client.py`, `lazy_proxy.py`, `task_tracker.py`, `api_utils.py`, `validation.py`, `rate_limiter.py`, `idempotency.py` | `tests/test_utils.py` (new) | 6h | ✅ |
| P2-2 | **Fix 16 skipped API tests** — set default `APP_PASSWORD` in test env | `tests/conftest.py` | 1h | ✅ |
| P2-3 | **Add responsive breakpoints** — 40/60 split stacks on mobile; Ollama/RAG hidden on small screens; badge hidden on mobile | `frontend/src/app/page.tsx`, `Header.tsx`, `ProgressPanel.tsx` | 3h | ✅ |
| P2-4 | **Convert `<div onClick>` to `<button>`** — ContactCard, GlobalSearch results, ProgressPanel expand | `Workspace.tsx`, `GlobalSearch.tsx`, `ProgressPanel.tsx` | 2h | ✅ |
| P2-5 | **Split useSyncStore mega-store** — 25 fields → auth/contacts/rag/status stores | `frontend/src/store/` (api.ts, authStore.ts, contactsStore.ts, ragStore.ts, statusStore.ts) + 8 component imports updated | 4h | ✅ |
| P2-6 | **Deep health check** — `/api/health?deep=true` probes ChromaDB, Redis, Ollama | `main_api.py`, `test_api_endpoints.py` | 1h | ✅ |
| P2-7 | **Signal handlers** — graceful shutdown for SIGTERM/SIGINT | `main_api.py` | 1h | ✅ |

---

### P3: Low Priority / Long-term

| ID | Task | Files | Effort | Status |
|---|---|---|---|---|
| P3-1 | **pytest-cov configuration** — add coverage reporting (68% overall) | `requirements-dev.txt`, `pyproject.toml` | 30m | ✅ |
| P3-2 | **Stale artifact cleanup** — `logs/error.log`, orphan `.pyc` in `tests/__pycache__/` | `logs/`, `tests/__pycache__/` | 5m | ✅ |
| P3-3 | **Service layer** — extract `_build_contacts_list`, `parse_monthly_messages`, `evaluate_connection_depth`, `get_contact_analytics` to `src/services/` | `src/services/contacts_service.py` (new), `api_contacts.py`, `api_tasks.py` | 4h | ✅ |
| P3-4 | **Dockerfile / docker-compose.yml** — non-Windows deployment | `Dockerfile.backend`, `docker-compose.yml`, `docker-compose.minimal.yml` | 2h | ✅ |
| P3-5 | **Distributed idempotency cache** — Redis-backed with in-memory fallback | `src/utils/idempotency.py` | 3h | ✅ |

---

## 3. Architecture Notes for Future Agents

### Key Patterns
- **Singleton via `__new__`**: `MetricsEngine`, `TranscriptionQueue` — use `ClassName()` anywhere to get same instance
- **LazyProxy**: `rag_engine`, `settings_manager`, `llm_dispatcher`, `task_tracker` — heavy init deferred to first access
- **Thread safety**: `RLock` for ChromaDB (`rag_engine`), `Lock` for SQLite (`metrics_engine`), `Queue` for transcription
- **No circular imports**: DAG is clean — `engine/` → `utils/`/`storage/`, `api/` → `engine/`/`utils/`

### What to Avoid
- Don't import `src.api.state` for engine access — use direct `MetricsEngine()`, `rag_engine`, etc.
- Don't add new module-level side effects — prefer explicit init in `main_api.py` lifespan
- Don't use `asyncio.get_event_loop()` — use `asyncio.get_running_loop()`

### Frontend State
- `authStore.ts`, `contactsStore.ts`, `ragStore.ts`, `statusStore.ts`: Individual stores (split from former mega-store)
- `taskStore.ts`: Background task polling (vacuum, analytics, reindex)
- `api.ts`: Shared fetch helpers, API types
- `useDebounce.ts` (in lib/): Shared debounced callback hook
- `StatusService`: WS → SSE → polling cascade with `StatusUpdatePayload`

---

## 4. Test Coverage Matrix

| Module | Test File | Coverage |
|---|---|---|
| `StorageManager` | `test_storage.py` | ✅ |
| `RAGEngine` | `test_rag_engine.py` | ✅ |
| `InstagramDataImporter` | `test_importer.py`, `test_e2e.py` | ✅ |
| `MetricsEngine` | `test_metrics_engine.py` | ✅ |
| `is_supported_json_message` | `test_is_supported_message.py` | ✅ |
| `self_healing.deduplicate_all_data` | `test_deduplication.py` | ✅ |
| `transcription_queue` | `test_parallel_transcription.py` | ✅ |
| `SettingsManager`, `LLMDispatcher`, `report_generator` | `test_personality_gui.py` | ✅ |
| FastAPI endpoints | `test_api_endpoints.py` | ✅ (52 tests) |
| `MediaProcessor` | `test_media_processor.py` | ✅ |
| `redis_client.py` | — | ❌ MISSING |
| `lazy_proxy.py` | — | ❌ MISSING |
| `task_tracker.py` | — | ❌ MISSING |
| `api_utils.py` | — | ❌ MISSING |
| `validation.py` | — | ❌ MISSING |
| `rate_limiter.py` | — | ❌ MISSING |
| `idempotency.py` | — | ❌ MISSING |

---

## 5. Quick Start for New Agent

```bash
# 1. Install deps
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. Run tests
PYTHONPATH=. python -m pytest tests/ -v

# 3. Run lint
ruff check src/ tests/
mypy src/

# 4. Frontend
cd frontend && npm install && npm run build
```

---

## 6. Next Actions (P1 Sprint — COMPLETED)

```
☑ P1-1: Fix WS reconnect bug (ws.ts:193)
☑ P1-2: Fix tsconfig paths alias
☑ P1-3: Add Toast accessibility
☑ P1-4: Remove unused Python deps
☑ P1-5: Remove unused JS deps
☑ P1-6: Rename test_broken.py → test_edge_cases.py
```

**After P1:** Run full test suite → `ruff check` → `mypy` → `npm run build` in frontend.

Then proceed to P0 security fixes.

---

## 7. Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-06-28 | Removed Instagram live sync entirely | User request; app now import-only |
| 2026-06-28 | Kept `INSTAGRAM_USERNAME` config | Used for "self" message identification |
| 2026-06-28 | Kept `httpx`, `websockets` as transitive deps | Needed by TestClient and uvicorn |
| 2026-06-28 | Kept `python-multipart` removal | No Form/File usage in routes |
| 2026-07-03 | P0 security fixes applied | Enforce bcrypt, rate-limit login, require SECRET_KEY |
| 2026-07-03 | Created `src/utils/markdown.py` | Consolidated 7 duplications of block-splitting pattern |
| 2026-07-03 | Renamed `useTaskStore.ts` → `taskStore.ts` | Consistent file naming convention across stores |

---

*End of Planning.md — Update this file after each task completion.*