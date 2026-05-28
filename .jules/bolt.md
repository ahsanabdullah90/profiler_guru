## 2025-05-15 - [Batching ChromaDB Upserts]
**Learning:** Batching `upsert` operations in ChromaDB (e.g., batch size 50) is significantly more efficient than individual operations, reducing import times by up to 6x. This is because it minimizes the overhead of separate transactions and potential network/IPC latency per record.
**Action:** Always prefer batching for bulk data ingestion into vector databases. Implement a buffer and a flush mechanism to handle both bulk and trailing data.

## 2025-05-15 - [Stable Hashing for Vector IDs]
**Learning:** Using Python's `hash()` for document IDs in vector databases like ChromaDB is unreliable because it is process-randomized. This leads to duplicate entries across restarts.
**Action:** Use a stable hashing algorithm like `hashlib.md5` for deterministic ID generation to ensure idempotency.
