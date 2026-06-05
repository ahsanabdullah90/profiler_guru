## 2025-05-15 - [Batched ChromaDB Indexing]
**Learning:** Batching `upsert` operations in ChromaDB significantly reduces the overhead of individual message indexing. Using a batch size of 50 resulted in a ~8.5x speedup (from ~370ms to ~44ms per message).
**Action:** Always prefer batched operations when indexing multiple documents to a vector database.

## 2025-05-15 - [Idempotent ID Generation]
**Learning:** Using Python's built-in `hash()` for persistent database IDs leads to data duplication across process restarts because `hash()` is randomized per process by default in Python 3.
**Action:** Use a stable hashing algorithm like `hashlib.md5` for generating persistent IDs to ensure idempotency.
