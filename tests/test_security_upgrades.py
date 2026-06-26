import os
import sqlite3
import tempfile
import pytest
import bcrypt
from pathlib import Path
from src.engine.metrics_engine import MetricsEngine
from src.utils.config import config
from src.app.streamlit_app import check_password
from src.engine.rag_engine import RAGEngine

def test_metrics_engine_migration_and_caching():
    # Clear singleton instance for clean test
    MetricsEngine._instance = None
    
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        # Create a legacy database first (without message_count in contact_metadata)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE connection_metrics (
                chat_name TEXT NOT NULL,
                date TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                PRIMARY KEY (chat_name, date)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE contact_metadata (
                chat_name TEXT PRIMARY KEY,
                last_snippet TEXT,
                last_date TEXT
            );
            """
        )
        # Populate legacy data
        conn.execute("INSERT INTO connection_metrics VALUES ('Alice', '2026-06-24', 5);")
        conn.execute("INSERT INTO connection_metrics VALUES ('Alice', '2026-06-25', 10);")
        conn.execute("INSERT INTO contact_metadata VALUES ('Alice', 'Hey!', '2026-06-25');")
        conn.commit()
        conn.close()
        
        # Initialize MetricsEngine on this legacy database (should trigger migration and backfill)
        engine = MetricsEngine(db_path=db_path)
        
        # Verify message_count column was added and correctly populated (5 + 10 = 15 messages)
        meta = engine.get_all_contact_metadata_with_counts()
        assert "Alice" in meta
        assert meta["Alice"]["message_count"] == 15
        assert meta["Alice"]["last_snippet"] == "Hey!"
        assert meta["Alice"]["last_date"] == "2026-06-25"
        
        # Verify get_contact_names works
        names = engine.get_contact_names()
        assert names == ["Alice"]
        
        # Verify increment_message updates both tables
        engine.increment_message("Alice", "2026-06-25")
        
        # The total count should now be 16
        meta = engine.get_all_contact_metadata_with_counts()
        assert meta["Alice"]["message_count"] == 16
        
    finally:
        # Cleanup
        if os.path.exists(str(db_path)):
            try:
                os.remove(str(db_path))
            except OSError:
                pass
        MetricsEngine._instance = None

def test_bcrypt_password_verification(monkeypatch):
    # Test case 1: bcrypt hash configured
    plaintext_password = "my_super_secret_password"
    hashed_password = bcrypt.hashpw(plaintext_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    monkeypatch.setattr(config, "APP_PASSWORD", hashed_password)
    
    # Mock streamlit session_state and text_input/button/etc.
    class SessionState:
        authenticated = False
        def __contains__(self, key):
            return key == "authenticated"
            
    import streamlit as st
    session_state = SessionState()
    monkeypatch.setattr(st, "session_state", session_state)
    
    # Helper to mock streamlit inputs and reruns
    rerun_called = []
    monkeypatch.setattr(st, "rerun", lambda: rerun_called.append(True))
    monkeypatch.setattr(st, "title", lambda *a, **k: None)
    monkeypatch.setattr(st, "error", lambda *a, **k: None)
    monkeypatch.setattr(st, "info", lambda *a, **k: None)
    monkeypatch.setattr(st, "stop", lambda: None)
    
    # Test correct password
    monkeypatch.setattr(st, "text_input", lambda *a, **k: plaintext_password)
    monkeypatch.setattr(st, "button", lambda *a, **k: True)
    
    result = check_password()
    assert session_state.authenticated is True
    assert len(rerun_called) == 1
    
    # Test case 2: plaintext password fallback
    session_state.authenticated = False
    rerun_called.clear()
    plaintext_config = "my_plain_password"
    monkeypatch.setattr(config, "APP_PASSWORD", plaintext_config)
    
    # Test incorrect password
    monkeypatch.setattr(st, "text_input", lambda *a, **k: "wrong_password")
    monkeypatch.setattr(st, "button", lambda *a, **k: True)
    
    result = check_password()
    assert session_state.authenticated is False
    assert len(rerun_called) == 0
    
    # Test correct plaintext password
    monkeypatch.setattr(st, "text_input", lambda *a, **k: plaintext_config)
    result = check_password()
    assert session_state.authenticated is True
    assert len(rerun_called) == 1

def test_tiktoken_token_counting():
    # Test tiktoken BPE counting in RAGEngine
    # Clear singleton instance for clean test
    RAGEngine._instance = None
    
    engine = RAGEngine()
    test_text = "This is a simple sentence to test tiktoken BPE token counting."
    
    # Estimate using our new tiktoken counter
    count = engine.estimate_token_count(test_text)
    
    # "This is a simple sentence to test tiktoken BPE token counting." is 14 tokens in cl100k_base
    assert count == 14

def test_transcription_queue_no_interleaving(tmp_path):
    """10 concurrent transcription tasks for the same file must not interleave."""
    import concurrent.futures, re
    from src.storage.storage_manager import StorageManager

    sm = StorageManager(str(tmp_path))
    chat_name = "TestContact"
    month = "2026_06"

    # Write 10 placeholder blocks
    file_path = tmp_path / chat_name / "Chats" / f"{month}.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    placeholder_times = [f"2026-06-01 00:{i:02d}:00" for i in range(10)]
    for ts in placeholder_times:
        block = f"### [{ts}] Bot\n[Audio Transcription: Processing...]\n<!-- chunk_id: deadbeef -->\n\n---\n"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(block)

    def update_one(ts):
        lock = StorageManager.get_lock(str(file_path))
        with lock:
            content = file_path.read_text(encoding="utf-8")
            blocks = content.split("---")
            for i, block in enumerate(blocks):
                if f"[{ts}]" in block and "[Audio Transcription: Processing...]" in block:
                    blocks[i] = block.replace(
                        "[Audio Transcription: Processing...]",
                        f"[Imported Audio Transcription: Result for {ts}]"
                    )
                    break
            file_path.write_text("---".join(blocks), encoding="utf-8")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(update_one, placeholder_times))

    final = file_path.read_text(encoding="utf-8")
    results = re.findall(r'\[Imported Audio Transcription: Result for .*?\]', final)
    assert len(results) == 10, f"Expected 10 results, got {len(results)}"
    assert "[Audio Transcription: Processing...]" not in final

def test_save_message_writes_chunk_id(tmp_path):
    import re
    from src.storage.storage_manager import StorageManager

    sm = StorageManager(str(tmp_path))
    content, file_path, month_id = sm.save_message(
        "ChunkTest", "Alice", "Hello, world!", 1750000000000
    )
    assert "<!-- chunk_id:" in content, "chunk_id comment not found in returned content"
    written = open(file_path, encoding="utf-8").read()
    assert re.search(r'<!--\s*chunk_id:\s*[a-f0-9]+\s*-->', written), \
        "chunk_id comment not found in written file"

def test_update_transcribed_message_deletes_old_vector(tmp_path):
    from src.engine.rag_engine import RAGEngine

    engine = RAGEngine(db_path=str(tmp_path / "chroma"))
    old_block = "### [2026-06-01 10:00:00] Alice\n[Audio Transcription: Processing...]\n<!-- chunk_id: aabbccdd -->\n"
    new_block = "### [2026-06-01 10:00:00] Alice\n[Imported Audio Transcription: Hello]\n<!-- chunk_id: aabbccdd -->\n"

    # First upsert the old block so it exists
    engine.add_messages_batch([("Alice", "2026_06", old_block)])

    # Now update — should delete old vectors and upsert new ones
    engine.update_transcribed_message("Alice", "2026_06", old_block, new_block)

    # Query should return the updated content
    results = engine.collection.get(where={"chat_name": "Alice"}, include=["documents"])
    docs = results.get("documents", [])
    assert any("Hello" in d for d in docs), "New transcription not found in ChromaDB"
    assert not any("Processing" in d for d in docs), "Old placeholder not deleted from ChromaDB"

def test_vacuum_removes_orphans(tmp_path, monkeypatch):
    from src.engine.rag_engine import RAGEngine
    from src.utils.config import config

    chats_dir = tmp_path / "chats"
    chats_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "CHATS_DIR", chats_dir)
    engine = RAGEngine(db_path=str(tmp_path / "chroma"))

    # Insert a dummy orphan directly into ChromaDB
    engine.collection.upsert(
        documents=["orphan content"],
        metadatas=[{"chat_name": "Ghost", "month": "2026_01", "date_range": "unknown", "chunk_index": 0}],
        ids=["Ghost_2026_01_orphanid_0"]
    )
    assert engine.collection.count() == 1

    # Run vacuum — no markdown files exist, so the orphan should be deleted
    deleted = engine.vacuum_orphaned_vectors()
    assert deleted == 1
    assert engine.collection.count() == 0

def test_pdf_html_escape_no_crash(tmp_path):
    from src.engine.report_generator import ReportGenerator

    rg = ReportGenerator()
    out_path = tmp_path / "test_report.pdf"
    content = (
        "## Summary\n"
        "The score is 5 < 10 and 20 > 15. Ratio: a & b. Quote: \"hello\".\n"
    )
    # Must not raise xml.parsers.expat.ExpatError or any XML crash
    rg.create_assessment_pdf(
        contact="TestUser",
        start_month="2026_01",
        end_month="2026_06",
        content=content,
        settings={"pdf_include_textual_profile": True, "pdf_include_charts": False,
                  "pdf_include_raw_snippets": False,
                  "report_sections_order": ["textual_profile"]},
        out_path=out_path
    )
    assert out_path.exists() and out_path.stat().st_size > 0

def test_ollama_timeout_config(monkeypatch):
    from src.utils.config import config
    from src.utils.ollama_client import OllamaClient

    monkeypatch.setattr(config, "OLLAMA_LIST_TIMEOUT", 42)
    monkeypatch.setattr(config, "OLLAMA_GENERATE_TIMEOUT", 99)

    client = OllamaClient()

    # Patch urlopen to capture the timeout argument
    captured = {}
    import urllib.request as ur

    def fake_urlopen(req, timeout=None):
        captured["timeout"] = timeout
        raise ConnectionRefusedError("mock")

    monkeypatch.setattr(ur, "urlopen", fake_urlopen)
    try:
        client.get_installed_models()
    except Exception:
        pass
    assert captured.get("timeout") == 42

    try:
        client.generate("llama3", "hello")
    except Exception:
        pass
    assert captured.get("timeout") == 99

def test_humanized_interval_clamped():
    from unittest.mock import patch
    from src.engine.instagram_sync import InstagramSync

    engine = InstagramSync.__new__(InstagramSync)   # skip __init__

    # Daytime — should be in [120, 1800]
    with patch("random.gauss", return_value=9999):
        val = engine._get_humanized_interval.__func__(engine)
    # Not testing the hour branch here; just clamp behavior
    assert 120.0 <= val <= 1800.0

def test_sync_stop_event_abort(monkeypatch):
    """Test that fetch_new_messages respects the stop event and aborts early."""
    import threading
    from unittest.mock import MagicMock
    from src.engine.instagram_sync import InstagramSync

    engine = InstagramSync.__new__(InstagramSync)   # skip __init__
    engine.cl = MagicMock()
    engine.write_lock = threading.Lock()
    engine.sync_progress_lock = threading.Lock()
    engine.sync_progress_current = 0
    engine.last_sync_time = {}
    engine.last_sync_run = {}
    engine.synced_message_ids = {}

    # Mock threads return
    mock_thread = MagicMock()
    mock_thread.id = "123"
    mock_thread.thread_title = "Test Abort"
    mock_thread.users = []
    
    engine.cl.direct_threads.return_value = [mock_thread, mock_thread, mock_thread]
    
    # Mock calls
    engine.sync_thread_messages = MagicMock()
    
    # Set up stop event and set it to abort early
    stop_event = threading.Event()
    stop_event.set()
    
    # Run fetch_new_messages
    engine.fetch_new_messages(stop_event=stop_event)
    
    # Should not have called sync_thread_messages due to early abort
    assert engine.sync_thread_messages.call_count == 0
