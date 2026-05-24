# Agent Instructions

## Documentation and Testing Policy
**Synchronization Requirement:** All changes to project documentation (e.g., `README.md`, docstrings, or architectural docs) MUST be accompanied by:
1. A review of existing tests in the `tests/` directory to ensure they are still valid.
2. Updates or additions to tests if the documentation describes new or changed behavior.
3. Updates to `tests/README.md` if the testing procedure changes.

## Coding Standards
- Use `pytest` for all new tests.
- Mock external APIs (Instagram, Google Gemini) in automated tests.
- Log architectural issues or bugs discovered in `tests/ISSUES_LOG.md`.

## Project Structure
- `src/engine/`: Core logic for sync, import, and RAG.
- `src/storage/`: File system management.
- `tests/`: Comprehensive test suite and testing docs.
