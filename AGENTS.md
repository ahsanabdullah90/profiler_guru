# Agent Instructions

This repository enforces strict guidelines for documentation synchronization and coding practices. AI agents pair-programming on this project must adhere to these policies.

---

## 1. Documentation & Testing Policy

**Synchronization Requirement:** All changes to project documentation (whether in `README.md`, files inside `docs/`, inline docstrings, or architectural files) MUST be accompanied by:
1. A review of existing tests in the `tests/` directory to ensure they remain valid.
2. Updates or additions to tests if the documentation describes new or changed behavior.
3. Updates to `docs/testing.md` or `tests/README.md` if the testing procedure or coverage changes.

---

## 2. Coding Standards

- **Pytest:** Use `pytest` for all new test cases.
- **Mocking:** Mock all external API services (Ollama, Google Gemini cloud engines, or network requests) to ensure the test suite executes offline.
- **Issues Log:** Log any new architectural concerns or bugs discovered in [tests/ISSUES_LOG.md](file:///f:/Github/Profile-Guru/tests/ISSUES_LOG.md).
- **Theme Tokens:** When editing frontend CSS or TSX, never hardcode background/text color classes. Always use semantic design tokens defined in `globals.css` (referenced in [docs/ui_ux.md](file:///f:/Github/Profile-Guru/docs/ui_ux.md)).
- **Consent Gate:** Ensure any new endpoints reading or modifying chat logs check patient permissions via [docs/consent_gate.md](file:///f:/Github/Profile-Guru/docs/consent_gate.md).

---

## 3. Project Directory Structure

For an explanation of the core modules, directories, and database tables, please consult:
- 🏗️ **[System Architecture](file:///f:/Github/Profile-Guru/docs/architecture.md)**
- 💾 **[Database Schema Reference](file:///f:/Github/Profile-Guru/docs/database_schema.md)**
- 🤝 **[Contributor Guidelines](file:///f:/Github/Profile-Guru/docs/contributing.md)**
