## 2025-05-15 - [Batching ChromaDB Upserts]
**Learning:** Batching message indexing in ChromaDB (every 50 messages) significantly reduces the overhead compared to individual insertions. According to project memory and measured impact, this achieved an ~8.5x speedup (reducing indexing time from ~360ms to ~42ms per message).
**Action:** Always prefer `collection.upsert` with a list of documents over individual `add` or `upsert` calls when dealing with bulk data ingestion.

## 2025-05-15 - [Stable ID Generation for Vector Databases]
**Learning:** Using the built-in `hash()` function for document IDs is dangerous because it's unstable across process restarts in Python (due to hash randomization). This can lead to duplicate entries and broken idempotency in the vector database.
**Action:** Use a stable hashing algorithm like `hashlib.md5` for generating document IDs to ensure they remain consistent across different runs and process restarts.
