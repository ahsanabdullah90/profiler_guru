# Profiler Guru Testing Documentation

This directory contains the automated test suite for Profile_Guru.

## Testing Strategy

The project follows a multi-level testing strategy:
- **Unit Tests:** Verify individual components like `StorageManager` and `RAGEngine` in isolation.
- **Integration Tests:** Verify the interaction between components, such as `InstagramDataImporter` and `StorageManager`.
- **End-to-End (E2E) Tests:** Verify the complete data flow from import to RAG query.
- **Mocking:** External services (Gemini AI via `google-generativeai`) are mocked to ensure tests are deterministic and can run without credentials.

## Prerequisites

Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
pip install pytest
```

## Running Tests

To run the full test suite, use the following command from the project root:
```bash
PYTHONPATH=. python3 -m pytest tests/
```

To run a specific test file:
```bash
PYTHONPATH=. python3 -m pytest tests/test_storage.py
```

## Test Directory Structure

- `conftest.py`: Contains shared pytest fixtures (e.g., temporary storage, mock RAG engine).  
  Sets `APP_PASSWORD` (bcrypt) and `SECRET_KEY` env vars via `pytest_configure` so config validation passes before any imports.
- `test_storage.py`: Tests for `StorageManager` (file system operations).
- `test_rag_engine.py`: Tests for `RAGEngine` (ChromaDB interactions and LLM integration).
- `test_importer.py`: Tests for `InstagramDataImporter`.
- `test_e2e.py`: End-to-end flow tests.
- `test_edge_cases.py`: Tests for known edge cases and error handling.
- `test_metrics_engine.py`: Tests for MetricsEngine (SQLite DB, daily stats, averages, backfill).
- `test_is_supported_message.py`: Tests for message filtering logic.
- `test_deduplication.py`: Tests for self-healing deduplication.
- `test_parallel_transcription.py`: Tests for background transcription queue.
- `test_personality_gui.py`: Tests for SettingsManager, LLMDispatcher, RAG snippets, PDF report generation.
- `test_api_endpoints.py`: Tests for FastAPI endpoints (auth, contacts, settings, RAG, reports, tasks, rate limiting, idempotency).
- `test_media_processor.py`: Tests for MediaProcessor (Gemini ASR, Whisper fallback).
- `test_inspector_store.py`: Unit tests for `InspectorStore` (thread-safe JSON store for tags, notes, flags; atomic writes; timestamped backups; corruption recovery).
- `test_inspector_api.py`: Integration tests for `/api/v1/inspector/*` endpoints (tags CRUD, notes CRUD, flags PATCH).
- `test_assessment_frameworks.py`: Tests for assessment framework definitions and routing.
- `test_scorers.py`: Tests for deterministic clinical scorers (PHQ-9, GAD-7, BHS) — 11 tests.
- `test_name_matcher.py`: Tests for fuzzy name matching (SequenceMatcher, partial token, Jaccard) — 13 tests.
- `test_contact_merge.py`: Tests for contact merge cascade (markdown, audio, SQLite, RAG) — 8 tests.
- `test_whatsapp_ingest.py`: Tests for WhatsApp ingest endpoint (text, audio, quoted, outgoing) — 9 tests.
- `test_knowledge_api.py`: Tests for knowledge base API endpoints.
- `test_ollama_client.py`: Tests for Ollama client wrapper.
- `test_user_notes_embedder.py`: Tests for user notes embedding pipeline.
- `test_model_size.py`: Tests for model size classification (large vs small).
- `test_sanitize.py`: Tests for input sanitization utilities.
- `test_utils.py`: Tests for utility modules (rate_limiter, validation, redis_client, lazy_proxy, task_tracker, api_utils, idempotency).
- `ISSUES_LOG.md`: A log of bugs or architectural issues discovered during testing.

## Adding New Tests

When adding new features:
1. Create a corresponding `test_*.py` file in the `tests/` directory.
2. Use fixtures from `conftest.py` where possible.
3. Mock external dependencies to keep tests fast and reliable.
4. Ensure all tests pass before submitting changes.

**Documentation Policy:** Any change to project documentation (e.g., README.md) must be accompanied by a review of these tests to ensure they still accurately reflect the documented behavior.

## Accessibility Testing (a11y)

The frontend enforces accessibility through a **static-analysis approach** (no Playwright/browser binary dependencies required for CI).

### How it works

- `frontend/eslint.config.mjs` enables the `jsx-a11y` plugin (bundled with `eslint-config-next`) at error level for critical rules:
  - `jsx-a11y/alt-text`
  - `jsx-a11y/label-has-associated-control`
  - `jsx-a11y/html-has-lang`
  - `jsx-a11y/heading-has-content`
  - `jsx-a11y/iframe-has-title`
  - `jsx-a11y/interactive-supports-focus`
  - `jsx-a11y/role-has-required-aria-props`
  - `jsx-a11y/role-supports-aria-props`
  - `jsx-a11y/tabindex-no-positive`
  - And more.
- `npm run lint` runs in `.github/workflows/ci.yml` on every PR. Errors block merge; warnings are reported but do not fail CI.
- Manual WCAG 2.1 AA checks are documented in `frontend/docs/DESIGN.md` (token contrast, min font size, focus rings, etc.).

### Why static instead of Playwright + axe-core

Playwright + axe-core would add ~100MB of browser binaries and a new dev dependency surface. The static jsx-a11y approach catches the most common regressions (missing labels, wrong roles, missing alt text, click handlers without keyboard equivalents) without slowing CI or adding new deps. A future phase can add Playwright + axe-core for runtime DOM checks if needed.

## CI

`.github/workflows/ci.yml` runs on every push and PR:
1. **Backend:** `python -m pytest tests/` (full suite, 97 tests).
2. **Frontend:** `npm ci && npm run build && npm run lint` (Next.js production build + a11y lint).
