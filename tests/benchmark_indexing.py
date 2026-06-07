import time
import os
import shutil
from src.engine.rag_engine import RAGEngine

def run_benchmark():
    # Setup fresh DB for benchmark
    db_path = "benchmark_chroma_db"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)

    # Mock RAGEngine to use benchmark path
    class BenchmarkRAGEngine(RAGEngine):
        def __init__(self, path):
            import chromadb
            from src.utils.config import config
            import google.generativeai as genai

            self.db_path = path
            self.client = chromadb.PersistentClient(path=self.db_path)
            self.model = None # Skip Gemini for indexing benchmark

            self.collection = self.client.get_or_create_collection(
                name="benchmark_messages",
                metadata={"hnsw:space": "cosine"}
            )

    engine = BenchmarkRAGEngine(db_path)

    num_messages = 200
    messages = [f"This is sample message number {i} for benchmarking indexing speed." for i in range(num_messages)]

    print(f"Benchmarking indexing of {num_messages} messages one by one...")

    start_time = time.time()
    for i, msg in enumerate(messages):
        engine.add_messages_to_index("test_chat", "2024_Q1", msg)
    end_time = time.time()

    total_time_individual = end_time - start_time
    avg_time_individual = (total_time_individual / num_messages) * 1000

    print(f"Total time (individual): {total_time_individual:.2f}s")
    print(f"Average time per message (individual): {avg_time_individual:.2f}ms")

    # Benchmark batched
    db_path_batched = "benchmark_chroma_db_batched"
    if os.path.exists(db_path_batched):
        shutil.rmtree(db_path_batched)
    engine = BenchmarkRAGEngine(db_path_batched)

    print(f"\nBenchmarking indexing of {num_messages} messages in batches of 50...")

    batch_size = 50
    start_time = time.time()
    for i in range(0, len(messages), batch_size):
        batch = [("test_chat", "2024_Q1", msg) for msg in messages[i:i+batch_size]]
        engine.add_messages_batch(batch)
    end_time = time.time()

    total_time_batched = end_time - start_time
    avg_time_batched = (total_time_batched / num_messages) * 1000

    print(f"Total time (batched): {total_time_batched:.2f}s")
    print(f"Average time per message (batched): {avg_time_batched:.2f}ms")

    speedup = total_time_individual / total_time_batched
    print(f"\nMeasured Speedup: {speedup:.2f}x")

    # Cleanup
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    if os.path.exists(db_path_batched):
        shutil.rmtree(db_path_batched)

    return avg_time_batched

if __name__ == "__main__":
    run_benchmark()
