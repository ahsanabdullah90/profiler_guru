# Profiler Guru Testing Documentation

This directory contains the automated test suite for Profile_Guru.

## Testing Strategy

The project follows a multi-level testing strategy:
- **Unit Tests:** Verify individual components like `StorageManager` and `RAGEngine` in isolation.
- **Integration Tests:** Verify the interaction between components, such as `InstagramDataImporter` and `StorageManager`.
- **End-to-End (E2E) Tests:** Verify the complete data flow from import/sync to RAG query.
- **Mocking:** External services (Instagram API via `instagrapi` and Gemini AI via `google-generativeai`) are mocked to ensure tests are deterministic and can run without credentials.

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
- `test_storage.py`: Tests for `StorageManager` (file system operations).
- `test_rag_engine.py`: Tests for `RAGEngine` (ChromaDB interactions and LLM integration).
- `test_importer.py`: Tests for `InstagramDataImporter`.
- `test_sync.py`: Tests for `InstagramSync`.
- `test_e2e.py`: End-to-end flow tests.
- `test_broken.py`: Tests for known edge cases and error handling.
- `ISSUES_LOG.md`: A log of bugs or architectural issues discovered during testing.

## Adding New Tests

When adding new features:
1. Create a corresponding `test_*.py` file in the `tests/` directory.
2. Use fixtures from `conftest.py` where possible.
3. Mock external dependencies to keep tests fast and reliable.
4. Ensure all tests pass before submitting changes.

**Documentation Policy:** Any change to project documentation (e.g., README.md) must be accompanied by a review of these tests to ensure they still accurately reflect the documented behavior.
