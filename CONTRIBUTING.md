# Contributing to Profiler Guru

Thank you for your interest in contributing to Profiler Guru! Please follow these guidelines to keep the codebase clean, stable, and well-documented.

---

## Code of Conduct
By contributing, you agree to uphold our [Code of Conduct](CODE_OF_CONDUCT.md) in all community and code interactions.

---

## Coding Standards

### 1. Python Style & Guidelines
- Write clean, PEP-8 compliant code.
- Always include descriptive docstrings for public classes and methods.
- Support bilingual context (Urdu & English) across all RAG query and voice transcription layers.
- Avoid absolute path strings; always use `config.DATA_DIR` or platform-agnostic `pathlib.Path` objects.

### 2. Testing Policy
- **Pytest First**: All new features must be covered by automated tests using `pytest`.
- **Mock External APIs**: Mock all network calls to external platforms (Instagram API, Google Gemini) in `conftest.py` or local test mocks to ensure tests are deterministic and can run offline.
- **No Residual Files**: Clean up temporary files or use pytest's `tmp_path` fixture for filesystem tests.

---

## Documentation Synchronization Policy

Our project maintains strict synchronization between documentation and testing. Any changes to documentation (such as `README.md`, architectural guides, or inline docstrings) must be accompanied by:
1. A review of existing tests in the `tests/` directory to ensure they remain valid.
2. Updates or additions to tests if the documentation describes new or changed behavior.
3. Updates to `tests/README.md` if the testing procedure changes.
