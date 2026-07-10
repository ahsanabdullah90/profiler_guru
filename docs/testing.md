# Testing Suite & Coverage

Profile Guru features a comprehensive test suite to verify RAG operations, SQLite metrics, media transcription fallbacks, and JWT security controls.

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

| Module / Class | Test File | Status |
| :--- | :--- | :--- |
| `StorageManager` | [test_storage.py](file:///f:/Github/Profile-Guru/tests/test_storage.py) | ✅ Verified |
| `RAGEngine` | [test_rag_engine.py](file:///f:/Github/Profile-Guru/tests/test_rag_engine.py), [test_rag_helpers.py](file:///f:/Github/Profile-Guru/tests/test_rag_helpers.py) | ✅ Verified |
| `InstagramDataImporter` | [test_importer.py](file:///f:/Github/Profile-Guru/tests/test_importer.py) | ✅ Verified |
| `MetricsEngine` | [test_metrics_engine.py](file:///f:/Github/Profile-Guru/tests/test_metrics_engine.py) | ✅ Verified |
| `MediaProcessor` | [test_media_processor.py](file:///f:/Github/Profile-Guru/tests/test_media_processor.py) | ✅ Verified |
| `TranscriptionQueue` | [test_parallel_transcription.py](file:///f:/Github/Profile-Guru/tests/test_parallel_transcription.py), [test_transcription_queue.py](file:///f:/Github/Profile-Guru/tests/test_transcription_queue.py) | ✅ Verified |
| `SettingsManager` | [test_personality_gui.py](file:///f:/Github/Profile-Guru/tests/test_personality_gui.py), [test_api_settings.py](file:///f:/Github/Profile-Guru/tests/test_api_settings.py) | ✅ Verified |
| `LLMDispatcher` | [test_personality_gui.py](file:///f:/Github/Profile-Guru/tests/test_personality_gui.py) | ✅ Verified |
| `ReportGenerator` | [test_personality_gui.py](file:///f:/Github/Profile-Guru/tests/test_personality_gui.py) | ✅ Verified |
| `InspectorStore` | [test_inspector_store.py](file:///f:/Github/Profile-Guru/tests/test_inspector_store.py), [test_inspector_api.py](file:///f:/Github/Profile-Guru/tests/test_inspector_api.py) | ✅ Verified |
| `Assessment Frameworks` | [test_assessment_frameworks.py](file:///f:/Github/Profile-Guru/tests/test_assessment_frameworks.py) | ✅ Verified |
| `Scorers (PHQ-9, GAD-7, BHS)` | [test_scorers.py](file:///f:/Github/Profile-Guru/tests/test_scorers.py) (11 tests) | ✅ Verified |
| `Name Matcher` | [test_name_matcher.py](file:///f:/Github/Profile-Guru/tests/test_name_matcher.py) (13 tests) | ✅ Verified |
| `Contact Merge` | [test_contact_merge.py](file:///f:/Github/Profile-Guru/tests/test_contact_merge.py) (8 tests) | ✅ Verified |
| `WhatsApp Ingest` | [test_whatsapp_ingest.py](file:///f:/Github/Profile-Guru/tests/test_whatsapp_ingest.py) (9 tests) | ✅ Verified |
| Utilities / Middleware | [test_utils.py](file:///f:/Github/Profile-Guru/tests/test_utils.py) | ✅ Verified |

---

## 4. Mocking External Services

To prevent tests from making actual cloud requests (which costs money and requires active internet connections):
- **Ollama Client Mocking:** `conftest.py` redirects Ollama requests to returns mock text responses representing completed profiles.
- **Gemini ASR Mocking:** In `test_media_processor.py`, API responses are mocked to return fixed transcript strings (e.g. Urdu/English translation blocks).
- **Database Mocking:** SQLite tests utilize in-memory databases (`sqlite3.connect(":memory:")`) or temp files that are torn down automatically after each test runs.
