# Known Issues & Limitations

This document tracks identified bugs, limitations, and architectural concerns in Profile Guru. These items are compiled from runtime logs and the internal [tests/ISSUES_LOG.md](file:///f:/Github/Profile-Guru/tests/ISSUES_LOG.md).

---

## 1. Core Engine Issues

### Issue 1: Invalid Timestamp Handling in `StorageManager.save_message()`
- **Symptom:** If an incoming message timestamp is corrupt or missing (e.g., from old Instagram JSON structures), the storage manager may default to the current system time or fail to parse the date directory.
- **Workaround:** Pre-validate and normalize timestamps in `data_importer.py` before passing values to `StorageManager`.

### Issue 2: Hardcoded ChromaDB Path in `RAGEngine.__init__()`
- **Symptom:** The path where ChromaDB stores persistent vectors is set directly in the initialization of RAGEngine rather than reading from `config.py` or `.env`. This limits custom data directory configuration on some servers.
- **Workaround:** Modify `rag_engine.py` to check `config.CHATS_DIR / "chroma_db"` at initialization.

### Issue 3: Partial Initialization of `MediaProcessor`
- **Symptom:** If both local GPU libraries (CUDA) and cloud AIStudio credentials are missing, `MediaProcessor` initializes in a degraded state without throwing an explicit warning. This can cause transcription requests to fail silently at runtime.
- **Workaround:** Add validation checks at startup inside `main_api.py` and display warning indicators in the Status Bar.

---

## 2. Platform Limitations

- **Group Chats Excluded:** The WhatsApp Bridge currently filters out all group chats (`chat.isGroup`) to prioritize individual patient profiling and protect group conversation privacy.
- **Bilingual Whisper Resource Intensity:** Running bilingual transcription (English + Urdu) locally via CPU-bound Whisper can be slow. We recommend setting up CUDA or using Google Gemini cloud ASR.
- **Single-Tenant Cosine Indexes:** Although ChromaDB uses `tenant_id` filters for search queries, all vectors are stored in a single unified collection. This requires careful tenant-id query injection to guarantee data separation.
