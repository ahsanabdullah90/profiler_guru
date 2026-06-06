## 2026-06-06 - [Batching ChromaDB Indexing]
**Learning:** Indexing messages individually into ChromaDB was a major bottleneck (~390ms/msg). Batching operations in blocks of 50 reduced this to ~66ms/msg, a ~5.8x speedup. It's also critical to ensure that batched content is pre-processed (e.g., splitting by separators) identically to individual indexing to maintain data integrity.
**Action:** Always look for batching opportunities when interacting with vector databases or external APIs. Use stable hashes (like MD5) for document IDs to ensure idempotency.
