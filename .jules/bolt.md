## 2025-06-11 - [Batched Vector Indexing]
**Learning:** Individual `upsert` calls to ChromaDB are extremely slow (~390ms per call) due to disk/network overhead. Batching these calls provides a ~9x measurable speedup. Using stable MD5 hashes for IDs ensures idempotency, avoiding duplicate entries across re-imports.
**Action:** Always prefer batched operations when indexing large volumes of text into a vector database. Implement a message buffer and flush at a reasonable threshold (e.g., 50 messages).
