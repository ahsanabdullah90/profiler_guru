# src/engine/metrics_engine.py
"""MetricsEngine handles daily/weekly connection‑depth metrics for contacts.
It stores data in a dedicated SQLite database (psych_profiles.db) using WAL mode.
Treats audio and text messages equally under a single message count.
"""
import os
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.utils.config import config
from src.utils.logger import logger
from src.utils.markdown import parse_message_blocks


class MetricsEngine:
    _instance = None
    _lock = threading.Lock()
    _write_lock: threading.Lock
    db_path: Path
    conn: sqlite3.Connection

    def __new__(cls, db_path: Path | None = None):
        with cls._lock:
            if cls._instance is None:
                if db_path is None:
                    db_path = Path(config.DATA_DIR) / "psych_profiles.db"
                cls._instance = super().__new__(cls)
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
        except Exception as e:
            logger.warning(f"Failed to close SQLite connection: {e}")

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
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS contact_metadata (
                chat_name TEXT PRIMARY KEY,
                last_snippet TEXT,
                last_date TEXT,
                message_count INTEGER DEFAULT 0
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                document_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                year INTEGER,
                embedding_status TEXT NOT NULL DEFAULT 'indexing',
                uploaded_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

        # Run database migration to add message_count column if it's missing (for legacy databases)
        try:
            cur.execute("SELECT message_count FROM contact_metadata LIMIT 1;")
        except sqlite3.OperationalError:
            logger.info("Migrating contact_metadata table to include message_count column...")
            try:
                cur.execute("ALTER TABLE contact_metadata ADD COLUMN message_count INTEGER DEFAULT 0;")
                self.conn.commit()

                # Backfill initial message counts by summing up connection_metrics
                cur.execute("SELECT chat_name, SUM(message_count) FROM connection_metrics GROUP BY chat_name;")
                rows = cur.fetchall()
                for chat_name, total_count in rows:
                    cur.execute(
                        """
                        INSERT INTO contact_metadata (chat_name, message_count, last_snippet, last_date)
                        VALUES (?, ?, '', '')
                        ON CONFLICT(chat_name) DO UPDATE SET message_count = ?;
                        """,
                        (chat_name, total_count, total_count)
                    )
                self.conn.commit()
                logger.info("contact_metadata migration and backfill completed successfully.")
            except Exception as migrate_err:
                logger.error(f"Failed to migrate contact_metadata: {migrate_err}")

    def update_contact_metadata(self, chat_name: str, last_snippet: str, last_date: str):
        """Updates the last message snippet and date for a contact."""
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO contact_metadata (chat_name, last_snippet, last_date)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_name) DO UPDATE SET
                    last_snippet = excluded.last_snippet,
                    last_date = excluded.last_date;
                """,
                (chat_name, last_snippet, last_date),
            )
            self.conn.commit()

    def get_all_contact_metadata_with_counts(self) -> dict:
        """Returns {chat_name: {"last_snippet": snippet, "last_date": date, "message_count": count}} for all contacts."""
        cur = self.conn.cursor()
        cur.execute("SELECT chat_name, last_snippet, last_date, message_count FROM contact_metadata;")
        return {
            row[0]: {
                "last_snippet": row[1] or "No messages imported yet.",
                "last_date": row[2] or "Never",
                "message_count": row[3] or 0
            }
            for row in cur.fetchall()
        }

    def get_contact_metadata(self, chat_name: str) -> dict | None:
        """Returns metadata for a single contact, or None if not found."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT chat_name, last_snippet, last_date, message_count FROM contact_metadata WHERE chat_name = ?;",
            (chat_name,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "last_snippet": row[1] or "No messages imported yet.",
            "last_date": row[2] or "Never",
            "message_count": row[3] or 0,
        }

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    @staticmethod
    def _resolve_date_str(timestamp) -> str:
        """Parse a timestamp into YYYY-MM-DD string.
        Supports epoch ms (int/float), ISO-8601 string, or YYYY-MM-DD string.
        """
        if isinstance(timestamp, int | float):
            return datetime.fromtimestamp(timestamp / 1000.0).strftime('%Y-%m-%d')
        elif isinstance(timestamp, str):
            if 'T' in timestamp:
                return timestamp.split('T')[0]
            elif ' ' in timestamp:
                return timestamp.split(' ')[0]
            else:
                return timestamp
        return datetime.now(UTC).strftime('%Y-%m-%d')

    def increment_message(self, chat_name: str, timestamp):
        """Increment message count for a given contact based on a message timestamp.
        Treats both audio and text messages as simple messages.
        `timestamp` can be epoch milliseconds (int/float), ISO-8601 string, or YYYY-MM-DD.
        """
        date_str = self._resolve_date_str(timestamp)

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
            # Also increment total message_count in contact_metadata
            cur.execute(
                """
                INSERT INTO contact_metadata (chat_name, message_count, last_snippet, last_date)
                VALUES (?, 1, '', '')
                ON CONFLICT(chat_name) DO UPDATE SET
                    message_count = message_count + 1;
                """,
                (chat_name,),
            )
            self.conn.commit()

    def increment_messages_batch(self, messages: list[tuple]):
        """Batch increment message counts. Single commit for all messages.
        messages: list of (chat_name, timestamp) tuples.
        """
        if not messages:
            return
        with self._write_lock:
            cur = self.conn.cursor()
            for chat_name, timestamp in messages:
                date_str = self._resolve_date_str(timestamp)

                cur.execute(
                    "INSERT INTO connection_metrics (chat_name, date, message_count) VALUES (?, ?, 1) "
                    "ON CONFLICT(chat_name, date) DO UPDATE SET message_count = message_count + 1;",
                    (chat_name, date_str),
                )
                cur.execute(
                    "INSERT INTO contact_metadata (chat_name, message_count, last_snippet, last_date) "
                    "VALUES (?, 1, '', '') ON CONFLICT(chat_name) DO UPDATE SET message_count = message_count + 1;",
                    (chat_name,),
                )
            self.conn.commit()

    def get_daily_stats(self, chat_name: str, days: int = 7):
        """Return a list of (date, message_count) for the last `days` days."""
        end_date = datetime.now(UTC).date()
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
        end_date = datetime.now(UTC).date()
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
        total_msg = int(result[0]) if result and result[0] is not None else 0
        return total_msg / float(days)

    def get_all_daily_averages(self, days: int = 7) -> dict:
        """Returns {chat_name: avg_daily_msgs} for ALL contacts in one query.
        This replaces N individual get_daily_average() calls with a single
        GROUP BY query, eliminating per-contact round-trip overhead.
        """
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=days - 1)
        cur = self.conn.cursor()
        cur.execute("""
            SELECT chat_name, SUM(message_count)
            FROM connection_metrics
            WHERE date BETWEEN ? AND ?
            GROUP BY chat_name;
        """, (start_date.isoformat(), end_date.isoformat()))
        return {row[0]: row[1] / float(days) for row in cur.fetchall()}

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
            batch = []
            try:
                with open(md_path, encoding="utf-8") as f:
                    content = f.read()

                blocks = parse_message_blocks(content)
                for block in blocks:
                    lines = block.split("\n")
                    header = lines[0].strip()
                    if header.startswith("### ["):
                        try:
                            closing_bracket_idx = header.find("]")
                            if closing_bracket_idx != -1:
                                time_str = header[5:closing_bracket_idx]
                                date_str = time_str.split()[0]
                                batch.append((chat_name, date_str))
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"Failed to backfill file {md_path}: {e}")

            if batch:
                self.increment_messages_batch(batch)

            if progress_callback:
                progress_callback(idx, total)

        self.set_backfill_done()

    def export_metrics(self, fmt: str = "csv") -> str:
        """Export all metrics to a temporary file and return its path.
        Supported formats: 'csv' or 'json'.
        """
        import csv
        import json
        import tempfile
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

    # -------- Knowledge Documents Helpers --------
    def add_knowledge_document(self, doc_id: str, filename: str, filepath: str, title: str, author: str | None, year: int | None, status: str = "indexing"):
        """Inserts a new knowledge document record into the SQLite DB."""
        uploaded_at = datetime.now().isoformat()
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO knowledge_documents (document_id, filename, filepath, title, author, year, embedding_status, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (doc_id, filename, filepath, title, author, year, status, uploaded_at)
            )
            self.conn.commit()

    def update_embedding_status(self, doc_id: str, status: str):
        """Updates the embedding indexing status for a document."""
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE knowledge_documents SET embedding_status = ? WHERE document_id = ?;",
                (status, doc_id)
            )
            self.conn.commit()

    def delete_knowledge_document(self, doc_id: str):
        """Deletes a knowledge document record by ID."""
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM knowledge_documents WHERE document_id = ?;", (doc_id,))
            self.conn.commit()

    def get_all_knowledge_documents(self) -> list[dict]:
        """Returns a list of all ingested knowledge documents."""
        cur = self.conn.cursor()
        cur.execute("SELECT document_id, filename, filepath, title, author, year, embedding_status, uploaded_at FROM knowledge_documents ORDER BY uploaded_at DESC;")
        rows = cur.fetchall()
        return [
            {
                "document_id": r[0],
                "filename": r[1],
                "filepath": r[2],
                "title": r[3],
                "author": r[4],
                "year": r[5],
                "embedding_status": r[6],
                "uploaded_at": r[7]
            }
            for r in rows
        ]
