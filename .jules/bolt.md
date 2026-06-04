## 2025-05-22 - [Batching ChromaDB Upserts]
**Learning:** Indexing messages individually in ChromaDB is a major bottleneck due to overhead in document processing and persistent storage writes. Batching multiple messages (e.g., 50) into a single `upsert` call significantly reduces IO wait time and improves ingestion throughput.
**Action:** Always prefer `add_messages_batch` (or equivalent batching methods) when importing large datasets or processing streams.
