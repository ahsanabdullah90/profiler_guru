# Contributor & Agent Guidelines

Thank you for contributing to Profile Guru! Please follow these guidelines to keep the codebase clean, stable, accessible, and well-documented.

---

## 1. Code Quality & Standards

### Python (Backend) Guidelines
- **PEP 8 Compliance:** All Python files must pass formatting and style checks. We use `ruff` as our linter and formatter.
- **Type Annotations:** Use type annotations for all function signatures and class definitions. Run `mypy` to verify typing correctness.
- **Descriptive Docstrings:** Provide docstrings (PEP 257) for all public classes, methods, and API routes.
- **Path Handling:** Never hardcode absolute path strings. Always use `config.py` path resolvers or platform-agnostic `pathlib.Path` objects.

Run the formatting and linting suite:
```bash
# Lint check
ruff check src/ tests/

# Type check
mypy src/
```

### TypeScript / Next.js (Frontend) Guidelines
- **Strict Linting:** We configure ESLint to enforce jsx-a11y and TypeScript rules at error level. All code must compile cleanly.
- **Theme Consistency:** Do not use legacy color utilities (`bg-zinc-800`, `text-zinc-300`, or direct hex colors). All custom UI styles must read from the CSS variable tokens (`var(--bg-canvas)`, `var(--brand-teal)`, etc.).

Run frontend validation:
```bash
cd frontend

# Lint check
npm run lint

# Production build check
npm run build
```

---

## 2. Testing Policy

- **Pytest First:** All backend features and API routes must be covered by automated tests using `pytest`.
- **Mock External APIs:** Network dependencies (Ollama HTTP endpoints, Google Gemini cloud clients, or external web scraping) must be fully mocked in `conftest.py` or local mocks to ensure that the test suite runs offline.
- **Filesystem Cleanup:** FS tests must use the pytest `tmp_path` fixture or clean up files immediately after execution.

---

## 3. Documentation Synchronization Policy

To prevent documentation rot, Profile Guru maintains strict synchronization between code, testing, and guides:
1. **Synchronized Updates:** Any change to project documentation (e.g., README files, architectural guides, or inline docstrings) must be accompanied by a review of the corresponding test files under `tests/`.
2. **Issue Logging:** If you discover a bug, security vulnerability, or architectural limitation, log the details immediately in [tests/ISSUES_LOG.md](file:///f:/Github/Profile-Guru/tests/ISSUES_LOG.md).
3. **Task Tracking:** Always update `AGENTS.md` and the internal task logs when adding or moving documentation files.
