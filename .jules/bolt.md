# Bolt Optimization Journal

## 2026-06-15 - [Batching RAG Upserts in Instagram Sync]
- **Problem:** Individual calls to `add_messages_to_index` caused N+1 upsert queries to ChromaDB during sync and import.
- **Solution:** Implemented `add_messages_batch` in `rag_engine.py` and refactored `instagram_sync.py` and `data_importer.py` to buffer messages and upsert them in batches.
- **Result:** Measured ~87.5% reduction in indexing time (from ~16.6s to ~2.1s for 50 messages).
- **Secondary Improvement:** Switched to `hashlib.md5` for ID generation to ensure stability across restarts.
