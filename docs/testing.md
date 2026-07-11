# Testing Suite & Coverage

Profile Guru features a comprehensive, dual-stack test suite:
- **Backend (Python/pytest):** 34 modules covering RAG operations, SQLite metrics, media transcription fallbacks, JWT security controls, clinical scorers, and API endpoints.
- **Frontend (TypeScript/Vitest):** 35 unit tests covering the `apiConfig` primitive layer, `api.ts` HTTP handling, `authStore`, and `contactsStore`.
- **Docs (Python):** Markdown link validator that scans all 55 `.md` files for broken `file:///` and relative links.

All three suites run automatically on every push via GitHub Actions CI.

---

## 1. Directory Structure of Tests

All test files are organized in the `tests/` directory:

```
tests/
├── README.md                    # Quick start for running tests
├── ISSUES_LOG.md                # Known issues and bug tracker
├── conftest.py                  # Pytest fixtures and mocks (Ollama, Gemini, DB)
├── test_api_endpoints.py        # Integration tests for FastAPI endpoints
├── test_api_settings.py         # Settings API endpoint tests
├── test_assessment_frameworks.py # Assessment framework definition and routing tests
├── test_assessment_queue.py     # Assessment background queue tests (not yet written)
├── test_contacts_api.py         # Testing contact cards listing & details
├── test_contact_merge.py        # Contact merge cascade tests (8 tests)
├── test_deduplication.py        # Testing clean JSON importing & deduplication
├── test_edge_cases.py           # Verification of empty inputs and invalid characters
├── test_e2e.py                  # Full path imports to RAG queries end-to-end tests
├── test_importer.py             # Data importer unit tests
├── test_inspector_api.py        # Inspector API integration tests
├── test_inspector_store.py      # InspectorStore unit tests
├── test_is_supported_message.py # Message filtering logic tests
├── test_knowledge_api.py        # Knowledge base API tests
├── test_media_processor.py      # Cloud ASR vs. local Whisper fallback tests
├── test_metrics_engine.py       # SQLite connection metrics and calculations tests
├── test_model_size.py           # Model size classification tests
├── test_name_matcher.py         # Fuzzy name matching tests (13 tests)
├── test_new_api_endpoints.py    # Newer API endpoint tests (clinical, consent, whatsapp)
├── test_ollama_client.py        # Ollama client wrapper tests
├── test_parallel_transcription.py # Testing concurrent audio queue jobs
├── test_personality_gui.py      # Personality Assessment & RAG Overhaul tests
├── test_rag_engine.py           # ChromaDB document indexing and snippet fetches tests
├── test_rag_helpers.py          # RAG helper function tests
├── test_sanitize.py             # Input sanitization tests
├── test_scorers.py              # Clinical scorer tests (PHQ-9, GAD-7, BHS) — 11 tests
├── test_storage.py              # StorageManager directory lock tests
├── test_transcription_queue.py  # Transcription queue internal tests
├── test_user_notes_embedder.py  # User notes embedding pipeline tests
├── test_utils.py                # Tests covering rate limiting, validation, and clients
└── test_whatsapp_ingest.py      # WhatsApp ingest endpoint tests (9 tests)
```

---

## 2. Command Line Operations

Make sure your virtual environment is active before running tests:

```bash
# Run the entire test suite
PYTHONPATH=. python -m pytest tests/ -v

# Run a specific test file
PYTHONPATH=. python -m pytest tests/test_rag_engine.py -v

# Run tests matching a specific query keyword
PYTHONPATH=. python -m pytest tests/ -k "consent"
```

### Coverage Reports
You can measure code coverage using the `pytest-cov` plugin:

```bash
# Generate terminal coverage report
PYTHONPATH=. python -m pytest --cov=src tests/

# Generate an HTML report (saved under htmlcov/)
PYTHONPATH=. python -m pytest --cov=src --cov-report=html tests/
```

---

## 3. Coverage Matrix

**Last measured:** 2026-07-11 · **Total:** 59% (3643 / 6224 statements)

> Run `PYTHONPATH=. python -m pytest tests/ --cov=src --cov-report=term-missing` to regenerate.

| Module / Area | Coverage | Key Gaps |
|:---|:---:|:---|
| `src/utils/sanitize.py` | **100%** | — |
| `src/utils/markdown.py` | **100%** | — |
| `src/assessment/frameworks.py` | **100%** | — |
| `src/storage/inspector_store.py` | **97%** | — |
| `src/utils/ollama_client.py` | **96%** | — |
| `src/utils/rate_limiter.py` | **95%** | — |
| `src/utils/task_tracker.py` | **94%** | — |
| `src/services/name_matcher.py` | **94%** | — |
| `src/assessment/scorers.py` | **91%** | — |
| `src/api/api_auth.py` | **91%** | — |
| `src/engine/settings_manager.py` | **91%** | — |
| `src/storage/storage_manager.py` | **90%** | — |
| `src/engine/transcription_queue.py` | **83%** | — |
| `src/api/api_inspector.py` | **86%** | — |
| `src/api/api_knowledge.py` | **79%** | — |
| `src/engine/metrics_engine.py` | 52% | Purge cascade, migration paths |
| `src/engine/rag_engine.py` | 58% | Streaming, deep-scan paths |
| `src/api/api_rag.py` | **65%** | SSE streaming endpoint |
| `src/api/api_models.py` | 20% | Model fetching, ThreadPoolExecutor parallelization |
| `src/api/api_contacts.py` | 42% | Photo upload/delete, pagination edge cases |
| `src/api/api_tasks.py` | 19% | Background task management endpoints |
| `src/assessment/pipeline.py` | 21% | Multi-step modular pipeline |
| `src/assessment/assessment_queue.py` | 21% | Background queue worker |
| `src/engine/llm_dispatcher.py` | 27% | Gemini/Ollama dispatch paths |

For test file → module mappings see the [Directory Structure](#1-directory-structure-of-tests) section above.



---

## 4. Mocking External Services

To prevent tests from making actual cloud requests (which costs money and requires active internet connections):
- **Ollama Client Mocking:** `conftest.py` redirects Ollama requests to returns mock text responses representing completed profiles.
- **Gemini ASR Mocking:** In `test_media_processor.py`, API responses are mocked to return fixed transcript strings (e.g. Urdu/English translation blocks).
- **Database Mocking:** SQLite tests utilize in-memory databases (`sqlite3.connect(":memory:")`) or temp files that are torn down automatically after each test runs.

---

## 5. Frontend Tests (TypeScript / Vitest)

Located in `frontend/src/__tests__/`. Run with `npm test` from the `frontend/` directory.

### Test Files

| Test File | What It Covers | Tests |
|---|---|---|
| [apiConfig.test.ts](file:///f:/Github/Profile-Guru/frontend/src/__tests__/apiConfig.test.ts) | Network constants, `getApiBase()`, `fetchWithTimeout` abort, token/auth-expiry bridges | 12 |
| [api.test.ts](file:///f:/Github/Profile-Guru/frontend/src/__tests__/api.test.ts) | `AuthError`, `ApiError`, `ValidationError` contracts, `apiFetch` 401/404/200 handling | 13 |
| [stores/authStore.test.ts](file:///f:/Github/Profile-Guru/frontend/src/__tests__/stores/authStore.test.ts) | `setAuthenticated` localStorage persistence, `login` happy/error, `verifyToken` no-token guard | 5 |
| [stores/contactsStore.test.ts](file:///f:/Github/Profile-Guru/frontend/src/__tests__/stores/contactsStore.test.ts) | `setSelectedContact` null safety, `client_id` vs `name` resolution, state clearing, `fetchContacts` error | 5 |

### Configuration

- **Framework:** [Vitest](https://vitest.dev/) v4.x with jsdom environment
- **Aliases:** `@/` resolves to `frontend/src/`
- **Coverage:** `npm run test:coverage` generates V8 HTML report
- **Config:** [vitest.config.ts](file:///f:/Github/Profile-Guru/frontend/vitest.config.ts)

---

## 6. Markdown Link Validation

```bash
python scripts/validate_links.py
```

Scans all `.md` files in the repository (excluding `node_modules`, `.git`, `.venv`) and verifies that:
- Relative links resolve to existing files/directories
- `file:///` absolute links resolve to existing paths on the local machine

Exits with code `0` on success, `1` on any broken links. Runs in CI under the `docs` job (no pip install required — stdlib only).

