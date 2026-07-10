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
├── test_contacts_api.py         # Testing contact cards listing & details
├── test_deduplication.py        # Testing clean JSON importing & deduplication
├── test_edge_cases.py           # Verification of empty inputs and invalid characters
├── test_e2e.py                  # Full path imports to RAG queries end-to-end tests
├── test_importer.py             # Data importer unit tests
├── test_media_processor.py      # Cloud ASR vs. local Whisper fallback tests
├── test_metrics_engine.py       # SQLite connection metrics and calculations tests
├── test_parallel_transcription.py # Testing concurrent audio queue jobs
├── test_personality_gui.py      # Personality Assessment & RAG Overhaul tests
├── test_rag_engine.py           # ChromaDB document indexing and snippet fetches tests
├── test_storage.py              # StorageManager directory lock tests
└── test_utils.py                # Tests covering rate limiting, validation, and clients
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
| `RAGEngine` | [test_rag_engine.py](file:///f:/Github/Profile-Guru/tests/test_rag_engine.py) | ✅ Verified |
| `InstagramDataImporter` | [test_importer.py](file:///f:/Github/Profile-Guru/tests/test_importer.py) | ✅ Verified |
| `MetricsEngine` | [test_metrics_engine.py](file:///f:/Github/Profile-Guru/tests/test_metrics_engine.py) | ✅ Verified |
| `MediaProcessor` | [test_media_processor.py](file:///f:/Github/Profile-Guru/tests/test_media_processor.py) | ✅ Verified |
| `TranscriptionQueue` | [test_parallel_transcription.py](file:///f:/Github/Profile-Guru/tests/test_parallel_transcription.py) | ✅ Verified |
| `SettingsManager` | [test_personality_gui.py](file:///f:/Github/Profile-Guru/tests/test_personality_gui.py) | ✅ Verified |
| `LLMDispatcher` | [test_personality_gui.py](file:///f:/Github/Profile-Guru/tests/test_personality_gui.py) | ✅ Verified |
| `ReportGenerator` | [test_personality_gui.py](file:///f:/Github/Profile-Guru/tests/test_personality_gui.py) | ✅ Verified |
| Utilities / Middleware | [test_utils.py](file:///f:/Github/Profile-Guru/tests/test_utils.py) | ✅ Verified |

---

## 4. Mocking External Services

To prevent tests from making actual cloud requests (which costs money and requires active internet connections):
- **Ollama Client Mocking:** `conftest.py` redirects Ollama requests to returns mock text responses representing completed profiles.
- **Gemini ASR Mocking:** In `test_media_processor.py`, API responses are mocked to return fixed transcript strings (e.g. Urdu/English translation blocks).
- **Database Mocking:** SQLite tests utilize in-memory databases (`sqlite3.connect(":memory:")`) or temp files that are torn down automatically after each test runs.
