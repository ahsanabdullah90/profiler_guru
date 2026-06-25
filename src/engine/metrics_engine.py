# src/engine/metrics_engine.py
"""MetricsEngine handles daily/weekly connection‑depth metrics for contacts.
It stores data in a dedicated SQLite database (psych_profiles.db) using WAL mode.
Treats audio and text messages equally under a single message count.
"""
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.utils.config import config
from src.utils.logger import logger

class MetricsEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Path = None):
        with cls._lock:
            if cls._instance is None:
                if db_path is None:
                    db_path = Path(config.DATA_DIR) / "psych_profiles.db"
                cls._instance = super(MetricsEngine, cls).__new__(cls)
                cls._instance._write_lock = threading.Lock()
                cls._instance._init_db(db_path)
            return cls._instance

    def _init_db(self, db_path: Path):
        self.db_path = db_path
        os.makedirs(self.db_path.parent, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        
        import atexit
        atexit.register(self.close)
        
        # Self-healing migration: if the old schema with audio_count exists, drop and recreate
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT audio_count FROM connection_metrics LIMIT 1;")
            logger.info("Old schema with audio_count detected. Recreating connection_metrics table...")
            cur.execute("DROP TABLE connection_metrics;")
            self.conn.commit()
        except sqlite3.OperationalError:
            # Table doesn't exist or doesn't have audio_count, which is fine
            pass
            
        self._create_tables()

    def close(self):
        """Closes the persistent SQLite database connection."""
        try:
            self.conn.close()
        except Exception:
            pass

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS connection_metrics (
                chat_name TEXT NOT NULL,
                date TEXT NOT NULL,  -- YYYY-MM-DD
                message_count INTEGER DEFAULT 0,
                PRIMARY KEY (chat_name, date)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self.conn.commit()

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def increment_message(self, chat_name: str, timestamp):
        """Increment message count for a given contact based on a message timestamp.
        Treats both audio and text messages as simple messages.
        `timestamp` can be epoch milliseconds (int/float), ISO-8601 string, or YYYY-MM-DD.
        """
        # Resolve date_str
        if isinstance(timestamp, (int, float)):
            date_str = datetime.fromtimestamp(timestamp / 1000.0).strftime('%Y-%m-%d')
        elif isinstance(timestamp, str):
            if 'T' in timestamp:
                date_str = timestamp.split('T')[0]  # ISO-8601
            elif ' ' in timestamp:
                date_str = timestamp.split(' ')[0]  # "YYYY-MM-DD HH:MM:SS"
            else:
                date_str = timestamp  # Assume YYYY-MM-DD
        else:
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO connection_metrics (chat_name, date, message_count)
                VALUES (?, ?, 1)
                ON CONFLICT(chat_name, date) DO UPDATE SET
                    message_count = message_count + 1;
                """,
                (chat_name, date_str),
            )
            self.conn.commit()

    def get_daily_stats(self, chat_name: str, days: int = 7):
        """Return a list of (date, message_count) for the last `days` days."""
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days - 1)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT date, message_count FROM connection_metrics
            WHERE chat_name = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC;
            """,
            (chat_name, start_date.isoformat(), end_date.isoformat()),
        )
        return cur.fetchall()

    def get_daily_average(self, chat_name: str, days: int = 7) -> float:
        """Return the true daily average message count over the last `days` days.
        Divides the total message count in the period by the total number of days,
        properly accounting for inactive days with 0 messages.
        """
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days - 1)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT SUM(message_count) FROM connection_metrics
            WHERE chat_name = ? AND date BETWEEN ? AND ?;
            """,
            (chat_name, start_date.isoformat(), end_date.isoformat()),
        )
        result = cur.fetchone()
        total_msg = result[0] if result and result[0] is not None else 0
        return total_msg / float(days)

    # ---------------------------------------------------------------------
    # Back‑fill logic
    # ---------------------------------------------------------------------
    def is_backfill_done(self) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key = 'backfill_done';")
        row = cur.fetchone()
        return row is not None and row[0] == '1'

    def set_backfill_done(self):
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('backfill_done', '1');")
            self.conn.commit()

    def backfill_existing_logs(self, progress_callback=None):
        """Iterate over existing markdown chat files and populate metrics.
        `progress_callback` receives (processed, total).
        """
        if self.is_backfill_done():
            return
        chat_root = Path(config.CHATS_DIR)
        if not chat_root.exists():
            if progress_callback:
                progress_callback(0, 0)
            self.set_backfill_done()
            return
            
        md_files = list(chat_root.rglob("*.md"))
        total = len(md_files)
        
        for idx, md_path in enumerate(md_files, start=1):
            chat_name = md_path.parent.parent.name
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                blocks = content.split("---")
                for block in blocks:
                    block = block.strip()
                    if not block:
                        continue
                    lines = block.split("\n")
                    header = lines[0].strip()
                    if header.startswith("### ["):
                        try:
                            closing_bracket_idx = header.find("]")
                            if closing_bracket_idx != -1:
                                time_str = header[5:closing_bracket_idx]
                                date_str = time_str.split()[0]  # YYYY-MM-DD
                                self.increment_message(chat_name, date_str)
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"Failed to backfill file {md_path}: {e}")
                
            if progress_callback:
                progress_callback(idx, total)
                
        self.set_backfill_done()

    def export_metrics(self, fmt: str = "csv") -> str:
        """Export all metrics to a temporary file and return its path.
        Supported formats: 'csv' or 'json'.
        """
        import tempfile, json, csv
        cur = self.conn.cursor()
        cur.execute("SELECT chat_name, date, message_count FROM connection_metrics ORDER BY chat_name, date;")
        rows = cur.fetchall()
        if fmt == "json":
            data = [{"chat_name": r[0], "date": r[1], "message_count": r[2]} for r in rows]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
            json.dump(data, tmp, indent=2)
        else:  # csv
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
            writer = csv.writer(tmp)
            writer.writerow(["chat_name", "date", "message_count"])
            writer.writerows(rows)
        tmp.close()
        return tmp.name
