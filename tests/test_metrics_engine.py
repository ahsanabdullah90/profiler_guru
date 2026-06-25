# tests/test_metrics_engine.py
import os
import sqlite3
import tempfile
from pathlib import Path
from src.engine.metrics_engine import MetricsEngine

from datetime import datetime, timezone

def test_metrics_engine_operations(monkeypatch):
    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)
            
        @classmethod
        def fromtimestamp(cls, timestamp, tz=None):
            return datetime.fromtimestamp(timestamp, tz)
            
    monkeypatch.setattr("src.engine.metrics_engine.datetime", MockDatetime)

    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        # Initialize engine with the temp db path
        # Clear singleton instance for testing
        MetricsEngine._instance = None
        engine = MetricsEngine(db_path=db_path)
        
        # Verify WAL mode is set
        conn = sqlite3.connect(str(db_path))
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert journal_mode.lower() == "wal"
        conn.close()
        
        # Test increment_message (both text and audio counted as simple messages)
        engine.increment_message("test_user", "2026-06-24T12:00:00")
        engine.increment_message("test_user", "2026-06-24T12:05:00")
        engine.increment_message("test_user", "2026-06-24T13:00:00")
        
        # Test increment_message with epoch timestamp (ms)
        # Dynamically compute epoch for 2026-06-24 12:00:00 in local timezone to be timezone-independent
        local_dt = datetime(2026, 6, 24, 12, 0, 0)
        local_epoch_ms = int(local_dt.timestamp() * 1000.0)
        engine.increment_message("test_user", local_epoch_ms)
        
        # Verify counts for 2026-06-24
        daily_stats = engine.get_daily_stats("test_user", days=1)
        assert len(daily_stats) == 1
        date, msg_count = daily_stats[0]
        assert date == "2026-06-24"
        assert msg_count == 4
        
        # Test daily averages (4 messages over 7 days = 4/7 = 0.57)
        avg_msg = engine.get_daily_average("test_user", days=7)
        assert abs(avg_msg - (4.0 / 7.0)) < 1e-5
        
        # Test monthly average (4 messages over 30 days = 4/30 = 0.133)
        avg_msg_30d = engine.get_daily_average("test_user", days=30)
        assert abs(avg_msg_30d - (4.0 / 30.0)) < 1e-5
        
        # Test export
        csv_path = engine.export_metrics(fmt="csv")
        assert os.path.exists(csv_path)
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 2  # header + 1 data row
        assert "test_user,2026-06-24,4" in lines[1]
        os.remove(csv_path)
        
        json_path = engine.export_metrics(fmt="json")
        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "test_user" in content
        assert '"message_count": 4' in content
        os.remove(json_path)
        
        # Test backfill flags
        assert not engine.is_backfill_done()
        engine.set_backfill_done()
        assert engine.is_backfill_done()
        
    finally:
        # Cleanup db files
        if os.path.exists(str(db_path)):
            try:
                os.remove(str(db_path))
            except OSError:
                pass
            # remove wal and shm files
            for suffix in [".db-wal", ".db-shm"]:
                p = str(db_path) + suffix
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
        # Reset singleton instance
        MetricsEngine._instance = None
