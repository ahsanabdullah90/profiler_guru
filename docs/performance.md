# Performance & Optimization

Profile Guru implements several optimizations to maintain quick response times and resource-efficiency when handling large DM history folders on local consumer hardware.

---

## 1. Context Truncation & Token Budgets

To prevent out-of-memory errors on local models or excessive API charges on cloud models:
- **Heuristic Truncation:** The backend measures context size before sending payloads to the LLM.
- **Local Ollama Budget:** Constrained to **15,000 characters** (approx. 3,000-4,000 tokens) to ensure fast local CPU/GPU execution.
- **Cloud Gemini Budget:** Allows up to **300,000 characters** to leverage deep context windows without truncation when consent is granted.
- **Tiktoken BPE Token Counting:** Computes prompt size using exact BPE (Byte-Pair Encoding) token counts rather than rough word-count heuristics.

---

## 2. SQLite Ingestion Batching

Importing tens of thousands of DMs can bottleneck disk operations. Profile Guru optimizes ingestion in the [historical import pipeline](file:///f:/Github/Profile-Guru/src/engine/data_importer.py):
- **Commit Batching:** Replaced per-message database commits with bulk insertions (`increment_messages_batch`) committing every 50 messages.
- **Loop Optimizations:** Moved timezone/datetime resolution out of inner message loops, and cached resolved file-system paths (`get_chat_paths`) per thread folder instead of repeating lookups per message.
- **WAL Mode Concurrency:** Configures SQLite Write-Ahead Logging to prevent thread congestion.

---

## 3. Caching & Memory Lifespans

- **Redis Contacts Cache:** Stores contact lists and true average calculations in Redis to avoid reading files from disk on every page reload.
- **Cache Invalidation:** The cache is automatically cleared (`invalidate_contacts_cache()`) when a new ZIP file is imported or two contacts are merged.
- **Broadcaster Task Lifespan:** Background tasks (such as progress broadcasters and vacuum tasks) are registered in a central lifecycle manager to ensure they are canceled on backend shutdown, preventing thread leaks.
- **Lazy Loaders:** Heavy dependencies (like the `faster-whisper` package and GenAI client instances) are loaded lazily upon first request rather than at server boot.

---

## 4. Concurrent Write Locking

To prevent race conditions when writing to the file system and ChromaDB:
- **SQLite locks:** Uses standard thread lock (`threading.Lock()`) for writing to `psych_profiles.db`.
- **ChromaDB client locks:** Implements a thread re-entrant write lock (`threading.RLock()`) over `rag_engine.py` calls to prevent index corruption during concurrent live ingestion.
