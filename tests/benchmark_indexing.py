import time
import os
import shutil
import hashlib
from src.engine.rag_engine import RAGEngine

def benchmark_indexing():
    # Setup a fresh engine
    db_path = "benchmark_db_temp"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)

    # Use a temporary database path for benchmarking to avoid clearing production data
    import chromadb
    client = chromadb.PersistentClient(path=db_path)
    engine = RAGEngine()
    engine.client = client
    engine.collection = client.get_or_create_collection(
        name="benchmark_collection",
        metadata={"hnsw:space": "cosine"}
    )

    chat_name = "BenchmarkChat"
    quarter = "2023_Q4"
    message_template = "### [2023-11-14 10:00:00] User\nThis is a test message number {}. It contains some text to be indexed.\n\n---\n"

    num_messages = 200
    messages = [message_template.format(i) for i in range(num_messages)]

    print(f"Benchmarking indexing of {num_messages} messages individually...")
    start_time = time.time()
    for msg in messages:
        engine.add_messages_to_index(chat_name, quarter, msg)
    end_time = time.time()
    individual_duration = end_time - start_time
    print(f"Individual indexing took: {individual_duration:.4f} seconds ({individual_duration/num_messages:.4f}s per message)")

    # Clear for batch test
    client_batch = chromadb.PersistentClient(path=db_path + "_batch")
    engine.client = client_batch
    engine.collection = client_batch.get_or_create_collection(
        name="benchmark_collection_batch",
        metadata={"hnsw:space": "cosine"}
    )

    print(f"Benchmarking indexing of {num_messages} messages in batches of 50...")
    batch_size = 50
    start_time = time.time()
    for i in range(0, num_messages, batch_size):
        batch = [(chat_name, quarter, msg) for msg in messages[i:i+batch_size]]
        engine.add_messages_batch(batch)
    end_time = time.time()
    batch_duration = end_time - start_time
    print(f"Batch indexing took: {batch_duration:.4f} seconds ({batch_duration/num_messages:.4f}s per message)")

    improvement = (individual_duration - batch_duration) / individual_duration * 100
    print(f"Performance improvement: {improvement:.2f}%")
    print(f"Speedup: {individual_duration / batch_duration:.2f}x")

if __name__ == "__main__":
    try:
        benchmark_indexing()
    finally:
        # Cleanup
        if os.path.exists("benchmark_db_temp"):
            shutil.rmtree("benchmark_db_temp")
        if os.path.exists("benchmark_db_temp_batch"):
            shutil.rmtree("benchmark_db_temp_batch")
