import pytest
import shutil
import os
from src.storage.storage_manager import StorageManager
from src.engine.rag_engine import RAGEngine

@pytest.fixture
def temp_storage(tmp_path):
    storage_dir = tmp_path / "test_chats"
    storage_dir.mkdir()
    return StorageManager(base_dir=str(storage_dir))

@pytest.fixture
def temp_rag_engine(tmp_path):
    db_path = tmp_path / "test_chroma_db"
    # Patch RAGEngine to use temp db_path
    engine = RAGEngine()
    engine.db_path = str(db_path)
    # We might need to re-initialize the client if it was already initialized in __init__
    import chromadb
    engine.client = chromadb.PersistentClient(path=engine.db_path)
    engine.collection = engine.client.get_or_create_collection(
        name="test_messages",
        metadata={"hnsw:space": "cosine"}
    )
    return engine

@pytest.fixture
def sample_messages():
    return [
        {"sender": "Alice", "text": "Hello there!", "timestamp": 1700000000000},
        {"sender": "Bob", "text": "Hi Alice!", "timestamp": 1700000060000},
    ]
