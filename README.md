# Profile Guru

> **📸 Multichannel Relationship Analytics & Clinical Behavioral Profiler**
>
> Profile Guru is a secure, HIPAA-compliant intelligence portal that ingests, indexes, and analyzes conversational data from Instagram Direct Messages and WhatsApp. Powered by a hybrid RAG (Retrieval-Augmented Generation) pipeline using ChromaDB and Google Gemini/Ollama, the application facilitates clinical behavioral profiling, deterministic psychological questionnaires, and semantic history search.

---

## Documentation Directory

The documentation has been restructured into dedicated guides located in the [docs/](file:///f:/Github/Profile-Guru/docs/) folder:

### Getting Started & Operations
- 🚀 **[Overview & Core Capabilities](file:///f:/Github/Profile-Guru/docs/overview.md)** — High-level product summary and technology stack.
- ⚙️ **[Installation & Setup Guide](file:///f:/Github/Profile-Guru/docs/setup.md)** — Virtual environments, Node packages, and env configurations.
- 💻 **[Operations & Usage Guide](file:///f:/Github/Profile-Guru/docs/usage.md)** — Running the batch launcher, manual imports, and starting the WhatsApp Bridge.

### Technical & Architectural Guides
- 🏗️ **[System Architecture](file:///f:/Github/Profile-Guru/docs/architecture.md)** — Decoupled client-server design, layer details, and singletons.
- 💾 **[Database Schema & Migrations](file:///f:/Github/Profile-Guru/docs/database_schema.md)** — SQLite WAL table structures, concurrent writing, and migrations.
- 💬 **[WhatsApp Bridge & Contact Merge](file:///f:/Github/Profile-Guru/docs/whatsapp_bridge.md)** — Puppeteer listener, live ingestion payloads, and the contact merge service.
- 🧠 **[Behavioral & Clinical Assessments](file:///f:/Github/Profile-Guru/docs/psychological_assessment.md)** — Single-pass vs. modular pipelines, PHQ-9/GAD-7 questionnaires, and PDF compilers.
- 🔒 **[Consent Gating & Data Protection](file:///f:/Github/Profile-Guru/docs/consent_gate.md)** — Patient data privacy, attestation logs, and validation middleware.
- 🔐 **[Encryption at Rest](file:///f:/Github/Profile-Guru/docs/encryption.md)** — Fernet (AES-128-CBC) encryption with OS keyring integration for clinical notes.
- 🗑️ **[Right-to-Be-Forgotten & Purge Cascade](file:///f:/Github/Profile-Guru/docs/purge_cascade.md)** — Patient data deletion across SQLite, filesystem, and vector stores with audit trail.
- 🚩 **[Feature Flags & Subscription Tiers](file:///f:/Github/Profile-Guru/docs/feature_flags.md)** — Free/pro tier gating system for subscription readiness.
- 🎨 **[UI/UX & Design Tokens](file:///f:/Github/Profile-Guru/docs/ui_ux.md)** — Semantic CSS variables, Recharts frames, onboarding flows, and accessibility.

### Optimization, Deployment & Testing
- ⚡ **[Performance Tuning](file:///f:/Github/Profile-Guru/docs/performance.md)** — Context truncation heuristics, DB batching, and Redis caches.
- 🐳 **[Deployment Guidelines](file:///f:/Github/Profile-Guru/docs/deployment.md)** — Docker Compose, production reverse proxies, and Linux setups.
- 🧪 **[Testing & Code Coverage](file:///f:/Github/Profile-Guru/docs/testing.md)** — Pytest test runner, mock configurations, and coverage tables.

### Project History & Policies
- ⚠️ **[Known Issues & Limitations](file:///f:/Github/Profile-Guru/docs/known_issues.md)** — Identified bugs and architectural issues.
- 🤝 **[Contributor Guidelines](file:///f:/Github/Profile-Guru/docs/contributing.md)** — Code style compliance, testing policies, and doc sync.
- 📜 **[Changelog](file:///f:/Github/Profile-Guru/docs/changelog.md)** — Detailed history of releases and sprint sprints.

---

## Quick Start (Local Run)

For Windows environments:

1. Copy `.env.example` to `.env` and fill in your keys.
2. Generate your app password hash and set it as `APP_PASSWORD`.
3. Double-click the batch file:
   ```bash
   run.bat
   ```

*For complete prerequisites and Unix instructions, see [docs/setup.md](file:///f:/Github/Profile-Guru/docs/setup.md).*

---

## Running Tests

### Backend (Python / pytest)

```bash
# From project root — runs all 34 test modules
PYTHONPATH=. python -m pytest tests/ -q

# With coverage report
PYTHONPATH=. python -m pytest tests/ --cov=src --cov-report=term-missing
```

### Frontend (TypeScript / Vitest)

```bash
cd frontend

npm test              # run once (CI mode)
npm run test:watch    # interactive watch mode
npm run test:coverage # with V8 coverage report
```

### Markdown Link Validation

```bash
# Scans all 55 markdown files for broken relative or file:/// links
python scripts/validate_links.py
```

> All three suites run automatically on every push via [GitHub Actions CI](.github/workflows/ci.yml).

---

## Security

For dependency audit findings, accepted risks, and the vulnerability reporting process, see [SECURITY.md](SECURITY.md).

