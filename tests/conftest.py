import pytest
import shutil
import os
import bcrypt


def pytest_configure():
    """Set default env vars so config validation passes in test environment.
    
    This MUST run before any src.* imports to avoid circular dependency issues
    with Config validation at module level.
    """
    import tempfile
    if not os.getenv("DATA_DIR"):
        test_data_dir = os.path.join(tempfile.gettempdir(), "profile_guru_test_data")
        os.environ["DATA_DIR"] = test_data_dir
        if os.path.exists(test_data_dir):
            try:
                shutil.rmtree(test_data_dir, ignore_errors=True)
            except Exception:
                pass

    if not os.getenv("APP_PASSWORD"):
        os.environ["APP_PASSWORD"] = bcrypt.hashpw(b"koko", bcrypt.gensalt()).decode()
    if not os.getenv("SECRET_KEY"):
        os.environ["SECRET_KEY"] = "test_secret_key_for_testing_only"

@pytest.fixture(autouse=True)
def _reset_login_rate_limiter():
    """Reset the login rate limiter before each test."""
    from src.api.api_auth import login_rate_limiter
    login_rate_limiter.history.clear()

@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset global singletons to prevent state leaking between tests."""
    from src.engine.metrics_engine import MetricsEngine
    MetricsEngine._instance = None
    yield
    MetricsEngine._instance = None

@pytest.fixture(autouse=True)
def _reset_rag_rate_limiter():
    """Reset the RAG rate limiter before each test."""
    try:
        from src.api.api_rag import rag_rate_limiter
        rag_rate_limiter.history.clear()
    except Exception:
        pass

@pytest.fixture(autouse=True)
def _use_local_embeddings(monkeypatch):
    """Use local embeddings matching the production setup (ollama + bge-m3)."""
    from src.utils.config import config
    monkeypatch.setattr(config, "EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setattr(config, "EMBEDDING_MODEL", "bge-m3")

@pytest.fixture
def temp_storage(tmp_path):
    from src.storage.storage_manager import StorageManager
    storage_dir = tmp_path / "test_chats"
    storage_dir.mkdir()
    return StorageManager(base_dir=str(storage_dir))

@pytest.fixture
def temp_rag_engine(tmp_path):
    from src.engine.rag_engine import RAGEngine
    db_path = tmp_path / "test_chroma_db"
    engine = RAGEngine()
    engine.db_path = str(db_path)
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
