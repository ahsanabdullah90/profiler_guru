# src/engine/metrics_engine.py
"""MetricsEngine handles daily/weekly connection‑depth metrics for contacts.
It stores data in a dedicated SQLite database (psych_profiles.db) using WAL mode.
Treats audio and text messages equally under a single message count.
"""
import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.utils.config import config
from src.utils.logger import logger
from src.utils.markdown import parse_message_blocks
from src.utils.sanitize import is_valid_uuid, generate_client_id, sanitize_contact_name


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
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reindex_state (
                chat_name     TEXT PRIMARY KEY,
                batch_id      TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'pending',
                retry_count   INTEGER DEFAULT 0,
                started_at    TEXT,
                completed_at  TEXT,
                error_msg     TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS contact_platforms (
                chat_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                first_seen TEXT,
                last_seen TEXT,
                message_count INTEGER DEFAULT 0,
                PRIMARY KEY (chat_name, platform)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_merges (
                suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                new_chat_name TEXT NOT NULL,
                existing_chat_name TEXT NOT NULL,
                reason TEXT NOT NULL,
                similarity REAL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            );
            """
        )
        self.conn.commit()

        # Ensure all clinical tables are initialized
        self._ensure_client_profiles_table()
        self._ensure_patient_consents_table()
        self._ensure_clinical_notes_table()
        self._ensure_assessment_history_table()
        self._ensure_session_audio_table()
        self._ensure_purged_patients_table()

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

        # UUID migration: add client_id columns if missing
        for table, columns in [
            ("client_profiles", ["client_id TEXT", "canonical_name TEXT"]),
            ("contact_metadata", ["client_id TEXT"]),
            ("connection_metrics", ["client_id TEXT"]),
            ("contact_platforms", ["client_id TEXT"]),
            ("reindex_state", ["client_id TEXT"]),
            ("clinical_notes", ["client_id TEXT"]),
            ("assessment_history", [
                "client_id TEXT",
                "patient_id TEXT",
                "framework_id TEXT",
                "generated_at TEXT",
                "file_path TEXT",
                "scores TEXT",
                "classification TEXT",
                "pipeline_mode TEXT",
                "total_steps INTEGER",
                "model_provider TEXT",
                "model_name TEXT",
                "summary TEXT"
            ]),
            ("session_audio", ["client_id TEXT"]),
            ("pending_merges", ["new_client_id TEXT", "existing_client_id TEXT"]),
        ]:
            for col_def in columns:
                col_name = col_def.split()[0]
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def};")
                    logger.info(f"Added {col_name} column to {table}")
                except sqlite3.OperationalError:
                    pass  # column already exists
        self.conn.commit()

    def resolve_contact(self, contact: str) -> tuple[str | None, str | None]:
        """Resolve a contact identifier to (client_id, chat_name).

        Accepts either a UUID or a chat_name string.
        Returns (None, None) if not found.
        """
        if is_valid_uuid(contact):
            row = self.conn.execute(
                "SELECT client_id, chat_name FROM client_profiles WHERE client_id = ?;",
                (contact,),
            ).fetchone()
            if row:
                return row[0], row[1]
            return None, None
        row = self.conn.execute(
            "SELECT client_id, chat_name FROM client_profiles WHERE chat_name = ?;",
            (contact,),
        ).fetchone()
        if row:
            return row[0], row[1]
        return contact, contact  # unknown contact — treat as chat_name

    def get_or_create_client_id(self, chat_name: str) -> str:
        """Return existing client_id for a chat_name, or create a new one."""
        row = self.conn.execute(
            "SELECT client_id FROM client_profiles WHERE chat_name = ?;",
            (chat_name,),
        ).fetchone()
        if row and row[0]:
            return row[0]
        cid = generate_client_id()
        canonical = self._canonical_name(chat_name)
        with self._write_lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO client_profiles (chat_name, client_id, canonical_name) VALUES (?, ?, ?);",
                (chat_name, cid, canonical),
            )
            self.conn.commit()
        return cid

    @staticmethod
    def _canonical_name(name: str) -> str:
        import re
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", name).strip().lower()
        return re.sub(r"\s+", " ", cleaned)

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
        cur.execute("SELECT chat_name, last_snippet, last_date, message_count, client_id FROM contact_metadata;")
        return {
            row[0]: {
                "last_snippet": row[1] or "No messages imported yet.",
                "last_date": row[2] or "Never",
                "message_count": row[3],
                "client_id": row[4],
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

    # -------- Reindex State Management --------

    def init_reindex_batch(self, contacts: list[str]):
        """Initialize a new reindex batch. Inserts all contacts as pending."""
        batch_id = datetime.now().isoformat()
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM reindex_state;")
            for contact in contacts:
                cur.execute(
                    "INSERT OR REPLACE INTO reindex_state (chat_name, batch_id, status) VALUES (?, ?, 'pending');",
                    (contact, batch_id)
                )
            self.conn.commit()
        logger.info(f"Initialized reindex batch '{batch_id}' with {len(contacts)} contacts")

    def get_pending_reindex_contacts(self) -> list[str]:
        """Return contacts with status 'pending' or 'indexing' (need processing)."""
        cur = self.conn.cursor()
        cur.execute("SELECT chat_name FROM reindex_state WHERE status IN ('pending', 'indexing') ORDER BY chat_name;")
        return [row[0] for row in cur.fetchall()]

    def get_reindex_total_contacts(self) -> int:
        """Count of all contacts in the current reindex batch."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM reindex_state;")
        row = cur.fetchone()
        return row[0] if row else 0

    def mark_contact_status(self, chat_name: str, status: str, error_msg: str | None = None):
        """Update a contact's reindex status and timestamps."""
        with self._write_lock:
            cur = self.conn.cursor()
            now = datetime.now().isoformat()
            if status == "indexing":
                cur.execute(
                    "UPDATE reindex_state SET status = ?, started_at = ? WHERE chat_name = ?;",
                    (status, now, chat_name)
                )
            elif status == "completed":
                cur.execute(
                    "UPDATE reindex_state SET status = ?, completed_at = ?, error_msg = NULL WHERE chat_name = ?;",
                    (status, now, chat_name)
                )
            elif status == "failed":
                cur.execute(
                    "UPDATE reindex_state SET status = ?, error_msg = ? WHERE chat_name = ?;",
                    (status, error_msg, chat_name)
                )
            else:
                cur.execute(
                    "UPDATE reindex_state SET status = ? WHERE chat_name = ?;",
                    (status, chat_name)
                )
            self.conn.commit()

    def increment_reindex_retry(self, chat_name: str) -> int:
        """Increment retry count for a failed contact. Returns the new count."""
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE reindex_state SET retry_count = retry_count + 1 WHERE chat_name = ?;",
                (chat_name,)
            )
            self.conn.commit()
            cur.execute("SELECT retry_count FROM reindex_state WHERE chat_name = ?;", (chat_name,))
            row = cur.fetchone()
            return row[0] if row else 0

    def get_reindex_retry_count(self, chat_name: str) -> int:
        """Get current retry count for a contact."""
        cur = self.conn.cursor()
        cur.execute("SELECT retry_count FROM reindex_state WHERE chat_name = ?;", (chat_name,))
        row = cur.fetchone()
        return row[0] if row else 0

    def clear_reindex_state(self):
        """Delete all reindex state after successful completion."""
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM reindex_state;")
            self.conn.commit()
        logger.info("Reindex state cleared")

    # -------- Client Profiles Management --------

    def _ensure_client_profiles_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS client_profiles (
                chat_name TEXT PRIMARY KEY,
                display_name TEXT,
                email TEXT,
                mobile TEXT,
                whatsapp TEXT,
                instagram_handle TEXT,
                photo_path TEXT,
                updated_at TEXT
            );
        """)
        # Migrate to v2: add patient_id, dob, mrn, consent_active columns
        for col_def in [
            ("patient_id", "TEXT"),
            ("dob", "TEXT"),
            ("mrn", "TEXT"),
            ("consent_active", "INTEGER DEFAULT 0"),
        ]:
            col_name = col_def[0]
            try:
                cur.execute(f"ALTER TABLE client_profiles ADD COLUMN {col_name} {col_def[1]};")
            except sqlite3.OperationalError:
                pass  # column already exists
        # Auto-assign patient_id for existing rows that don't have one
        cur.execute("SELECT chat_name FROM client_profiles WHERE patient_id IS NULL;")
        rows = cur.fetchall()
        for (cn,) in rows:
            pid = str(uuid.uuid4())[:12]
            cur.execute("UPDATE client_profiles SET patient_id = ? WHERE chat_name = ?;", (pid, cn))
        self.conn.commit()

    def _ensure_patient_consents_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS patient_consents (
                consent_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                consent_type TEXT NOT NULL,
                attested_by TEXT NOT NULL DEFAULT 'practitioner',
                consent_version TEXT NOT NULL,
                attested_at TEXT NOT NULL,
                revoked_at TEXT,
                notes TEXT
            );
        """)
        self.conn.commit()

    def _ensure_clinical_notes_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clinical_notes (
                note_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                session_date TEXT NOT NULL,
                note_type TEXT NOT NULL DEFAULT 'free',
                note_text TEXT NOT NULL,
                consent_version TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                revised_from TEXT,
                deleted_at TEXT
            );
        """)
        self.conn.commit()

    def get_client_profile(self, contact: str) -> dict | None:
        self._ensure_client_profiles_table()
        cur = self.conn.cursor()
        if is_valid_uuid(contact):
            cur.execute("SELECT display_name, email, mobile, whatsapp, instagram_handle, photo_path, updated_at, patient_id, dob, mrn, consent_active, client_id, chat_name FROM client_profiles WHERE client_id = ?;", (contact,))
        else:
            cur.execute("SELECT display_name, email, mobile, whatsapp, instagram_handle, photo_path, updated_at, patient_id, dob, mrn, consent_active, client_id, chat_name FROM client_profiles WHERE chat_name = ?;", (contact,))
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "display_name": row[0],
            "email": row[1],
            "mobile": row[2],
            "whatsapp": row[3],
            "instagram_handle": row[4],
            "photo_path": row[5],
            "updated_at": row[6],
            "patient_id": row[7],
            "dob": row[8],
            "mrn": row[9],
            "consent_active": bool(row[10]),
            "client_id": row[11],
            "chat_name": row[12],
        }

    def get_patient_by_id(self, patient_id: str) -> dict | None:
        self._ensure_client_profiles_table()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT chat_name, display_name, email, mobile, whatsapp, instagram_handle, photo_path, updated_at, patient_id, dob, mrn, consent_active "
            "FROM client_profiles WHERE patient_id = ?;", (patient_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "chat_name": row[0],
            "display_name": row[1],
            "email": row[2],
            "mobile": row[3],
            "whatsapp": row[4],
            "instagram_handle": row[5],
            "photo_path": row[6],
            "updated_at": row[7],
            "patient_id": row[8],
            "dob": row[9],
            "mrn": row[10],
            "consent_active": bool(row[11]),
        }

    def upsert_client_profile(self, chat_name: str, display_name: str | None = None, email: str | None = None, mobile: str | None = None, whatsapp: str | None = None, instagram_handle: str | None = None):
        self._ensure_client_profiles_table()
        now = datetime.now().isoformat()
        cid = self.get_or_create_client_id(chat_name)
        canonical = self._canonical_name(chat_name)
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO client_profiles (chat_name, client_id, canonical_name, display_name, email, mobile, whatsapp, instagram_handle, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_name) DO UPDATE SET
                    client_id = COALESCE(?, client_id),
                    canonical_name = COALESCE(?, canonical_name),
                    display_name = COALESCE(?, display_name),
                    email = COALESCE(?, email),
                    mobile = COALESCE(?, mobile),
                    whatsapp = COALESCE(?, whatsapp),
                    instagram_handle = COALESCE(?, instagram_handle),
                    updated_at = ?;
            """, (chat_name, cid, canonical, display_name, email, mobile, whatsapp, instagram_handle, now,
                  cid, canonical, display_name, email, mobile, whatsapp, instagram_handle, now))
            self.conn.commit()

    def upsert_client_profile_full(self, chat_name: str, profile: dict):
        self._ensure_client_profiles_table()
        now = datetime.now().isoformat()
        cid = self.get_or_create_client_id(chat_name)
        canonical = self._canonical_name(chat_name)
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO client_profiles (chat_name, client_id, canonical_name, display_name, email, mobile, whatsapp, instagram_handle, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_name) DO UPDATE SET
                    client_id = COALESCE(?, client_id),
                    canonical_name = COALESCE(?, canonical_name),
                    display_name = excluded.display_name,
                    email = excluded.email,
                    mobile = excluded.mobile,
                    whatsapp = excluded.whatsapp,
                    instagram_handle = excluded.instagram_handle,
                    updated_at = excluded.updated_at;
            """, (
                chat_name,
                cid,
                canonical,
                profile.get("display_name"),
                profile.get("email"),
                profile.get("mobile"),
                profile.get("whatsapp"),
                profile.get("instagram_handle"),
                now,
                cid,
                canonical,
            ))
            self.conn.commit()

    def update_patient_profile(self, patient_id: str, profile: dict):
        """Update patient-level fields (dob, mrn, display_name, etc.) by patient_id."""
        self._ensure_client_profiles_table()
        now = datetime.now().isoformat()
        dob = profile.get("dob")
        mrn = profile.get("mrn")
        display_name = profile.get("display_name")
        with self._write_lock:
            cur = self.conn.cursor()
            updates = []
            params = []
            if dob is not None:
                updates.append("dob = ?")
                params.append(dob)
            if mrn is not None:
                updates.append("mrn = ?")
                params.append(mrn)
            if display_name is not None:
                updates.append("display_name = ?")
                params.append(display_name)
            if not updates:
                return
            updates.append("updated_at = ?")
            params.append(now)
            params.append(patient_id)
            cur.execute(
                f"UPDATE client_profiles SET {', '.join(updates)} WHERE patient_id = ?;",
                params,
            )
            self.conn.commit()

    def set_consent_active(self, patient_id: str, active: bool):
        self._ensure_client_profiles_table()
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("UPDATE client_profiles SET consent_active = ?, updated_at = ? WHERE patient_id = ?;",
                        (1 if active else 0, datetime.now().isoformat(), patient_id))
            self.conn.commit()

    # -------- Patient Consents Management --------

    def add_consent_attestation(self, patient_id: str, consent_type: str, consent_version: str, notes: str = "") -> dict:
        self._ensure_patient_consents_table()
        now = datetime.now().isoformat()
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO patient_consents (patient_id, consent_type, attested_by, consent_version, attested_at, notes)
                VALUES (?, ?, 'practitioner', ?, ?, ?);
            """, (patient_id, consent_type, consent_version, now, notes))
            consent_id = cur.lastrowid
            self.conn.commit()
        return {"consent_id": consent_id, "patient_id": patient_id, "consent_type": consent_type,
                "consent_version": consent_version, "attested_at": now, "revoked_at": None}

    def revoke_consent(self, patient_id: str, consent_type: str):
        self._ensure_patient_consents_table()
        now = datetime.now().isoformat()
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("""
                UPDATE patient_consents SET revoked_at = ? WHERE patient_id = ? AND consent_type = ? AND revoked_at IS NULL;
            """, (now, patient_id, consent_type))
            self.conn.commit()
        # Also update the denormalized flag
        active_any = self.has_active_consent(patient_id, "chat_analysis") or \
                     self.has_active_consent(patient_id, "audio_recording") or \
                     self.has_active_consent(patient_id, "clinical_assessment")
        self.set_consent_active(patient_id, active_any)

    def get_active_consents(self, patient_id: str) -> list[dict]:
        self._ensure_patient_consents_table()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT consent_id, patient_id, consent_type, attested_by, consent_version, attested_at, revoked_at, notes
            FROM patient_consents WHERE patient_id = ? AND revoked_at IS NULL;
        """, (patient_id,))
        rows = cur.fetchall()
        return [
            {"consent_id": r[0], "patient_id": r[1], "consent_type": r[2], "attested_by": r[3],
             "consent_version": r[4], "attested_at": r[5], "revoked_at": r[6], "notes": r[7]}
            for r in rows
        ]

    def get_consent_history(self, patient_id: str) -> list[dict]:
        self._ensure_patient_consents_table()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT consent_id, patient_id, consent_type, attested_by, consent_version, attested_at, revoked_at, notes
            FROM patient_consents WHERE patient_id = ? ORDER BY attested_at DESC;
        """, (patient_id,))
        rows = cur.fetchall()
        return [
            {"consent_id": r[0], "patient_id": r[1], "consent_type": r[2], "attested_by": r[3],
             "consent_version": r[4], "attested_at": r[5], "revoked_at": r[6], "notes": r[7]}
            for r in rows
        ]

    def has_active_consent(self, patient_id: str, consent_type: str) -> bool:
        self._ensure_patient_consents_table()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM patient_consents WHERE patient_id = ? AND consent_type = ? AND revoked_at IS NULL;
        """, (patient_id, consent_type))
        count = cur.fetchone()[0]
        return count > 0

    def update_client_profile_photo(self, chat_name: str, photo_path: str):
        self._ensure_client_profiles_table()
        now = datetime.now().isoformat()
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO client_profiles (chat_name, photo_path, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_name) DO UPDATE SET
                    photo_path = excluded.photo_path,
                    updated_at = excluded.updated_at;
            """, (chat_name, photo_path, now))
            self.conn.commit()

    def delete_client_profile_photo(self, chat_name: str):
        self._ensure_client_profiles_table()
        now = datetime.now().isoformat()
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("UPDATE client_profiles SET photo_path = NULL, updated_at = ? WHERE chat_name = ?;", (now, chat_name))
            self.conn.commit()

    def get_all_profiles(self) -> dict[str, dict]:
        self._ensure_client_profiles_table()
        cur = self.conn.cursor()
        cur.execute("SELECT chat_name, display_name, email, mobile, whatsapp, instagram_handle, photo_path FROM client_profiles;")
        result = {}
        for row in cur.fetchall():
            result[row[0]] = {
                "display_name": row[1],
                "email": row[2],
                "mobile": row[3],
                "whatsapp": row[4],
                "instagram_handle": row[5],
                "photo_path": row[6],
            }
        return result

    # -------- Assessment History --------

    def _ensure_assessment_history_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS assessment_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                contact_name TEXT NOT NULL,
                framework_id TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                file_path TEXT,
                scores TEXT,
                classification TEXT,
                pipeline_mode TEXT,
                total_steps INTEGER,
                model_provider TEXT,
                model_name TEXT,
                summary TEXT
            );
        """)
        self.conn.commit()

    def save_assessment_metadata(self, contact_name: str, meta: dict, file_path: str | None = None) -> int:
        """Record an assessment run in the history table.

        Returns the history_id of the new record.
        """
        self._ensure_assessment_history_table()
        profile = self.get_client_profile(contact_name)
        patient_id = profile.get("patient_id") if profile else None
        scores = meta.get("scores")
        now = datetime.now().isoformat()
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                """INSERT INTO assessment_history
                   (patient_id, contact_name, framework_id, generated_at, file_path, scores, classification,
                    pipeline_mode, total_steps, model_provider, model_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (
                    patient_id,
                    contact_name,
                    meta.get("framework_id", ""),
                    now,
                    file_path,
                    json.dumps(scores) if scores else None,
                    meta.get("classification"),
                    meta.get("pipeline_mode", "single"),
                    meta.get("total_steps", 1),
                    meta.get("model_provider"),
                    meta.get("model_name"),
                ),
            )
            history_id = cur.lastrowid
            self.conn.commit()
        return history_id

    def get_assessment_history(self, contact_name: str, limit: int = 50) -> list[dict]:
        self._ensure_assessment_history_table()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT history_id, framework_id, generated_at, scores, classification, pipeline_mode, model_name, summary "
            "FROM assessment_history WHERE contact_name = ? ORDER BY generated_at DESC LIMIT ?;",
            (contact_name, limit),
        )
        rows = cur.fetchall()
        result = []
        for r in rows:
            scores_raw = r[3]
            result.append({
                "history_id": r[0],
                "framework_id": r[1],
                "generated_at": r[2],
                "scores": json.loads(scores_raw) if scores_raw else None,
                "classification": r[4],
                "pipeline_mode": r[5],
                "model_name": r[6],
                "summary": r[7],
            })
        return result

    # -------- Session Audio --------

    def _ensure_session_audio_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS session_audio (
                session_id TEXT PRIMARY KEY,
                patient_id TEXT,
                contact_name TEXT NOT NULL,
                audio_path TEXT NOT NULL,
                original_filename TEXT,
                uploaded_at TEXT NOT NULL,
                transcribed_at TEXT,
                transcript TEXT,
                consent_version TEXT,
                duration_seconds INTEGER
            );
        """)
        self.conn.commit()

    def save_session_audio(self, contact_name: str, audio_path: str, original_filename: str | None = None, consent_version: str | None = None) -> dict:
        import uuid
        from datetime import UTC, datetime
        self._ensure_session_audio_table()
        session_id = str(uuid.uuid4())[:12]
        now = datetime.now(UTC).isoformat()
        profile = self.get_client_profile(contact_name)
        patient_id = profile.get("patient_id") if profile else None
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO session_audio (session_id, patient_id, contact_name, audio_path, original_filename, uploaded_at, consent_version) "
                "VALUES (?, ?, ?, ?, ?, ?, ?);",
                (session_id, patient_id, contact_name, audio_path, original_filename, now, consent_version),
            )
            self.conn.commit()
        return {"session_id": session_id, "audio_path": audio_path, "uploaded_at": now}

    def update_session_transcript(self, session_id: str, transcript: str, duration: int | None = None):
        self._ensure_session_audio_table()
        now = __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE session_audio SET transcribed_at = ?, transcript = ?, duration_seconds = COALESCE(?, duration_seconds) WHERE session_id = ?;",
                (now, transcript, duration, session_id),
            )
            self.conn.commit()

    def get_session_audio(self, contact_name: str) -> list[dict]:
        self._ensure_session_audio_table()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT session_id, audio_path, original_filename, uploaded_at, transcribed_at, transcript, duration_seconds "
            "FROM session_audio WHERE contact_name = ? ORDER BY uploaded_at DESC;",
            (contact_name,),
        )
        rows = cur.fetchall()
        return [
            {
                "session_id": r[0],
                "audio_path": r[1],
                "original_filename": r[2],
                "uploaded_at": r[3],
                "transcribed_at": r[4],
                "transcript": r[5],
                "duration_seconds": r[6],
            }
            for r in rows
        ]

    # -------- Right-to-be-Forgotten --------

    def _ensure_purged_patients_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS purged_patients (
                patient_id TEXT PRIMARY KEY,
                purged_at TEXT NOT NULL,
                purged_by TEXT DEFAULT 'practitioner',
                reason TEXT,
                records_deleted INTEGER DEFAULT 0
            );
        """)
        self.conn.commit()

    def purge_patient(self, patient_id_or_contact: str) -> dict:
        """Cascade-delete all data for a patient across ALL stores.

        This includes: client_profiles, patient_consents, clinical_notes,
        assessment_history, session_audio, chat files, Audio files, photos,
        ChromaDB vectors, and personality assessment files.

        Writes a tombstone to purged_patients table.
        """
        import shutil
        from datetime import UTC, datetime
        self._ensure_purged_patients_table()
        now = datetime.now(UTC).isoformat()

        # Resolve patient_id
        pid = patient_id_or_contact
        profile = self.get_patient_by_id(pid)
        if profile is None:
            profile = self.get_client_profile(pid)
            if profile and profile.get("patient_id"):
                patient_id = profile["patient_id"]
            else:
                return {"status": "not_found", "patient_id": pid}
        else:
            patient_id = pid

        deleted_count = 0

        with self._write_lock:
            cur = self.conn.cursor()

            # 1. Delete patient_consents
            cur.execute("DELETE FROM patient_consents WHERE patient_id = ?;", (patient_id,))
            deleted_count += cur.rowcount

            # 2. Delete clinical_notes (hard delete)
            cur.execute("DELETE FROM clinical_notes WHERE patient_id = ?;", (patient_id,))
            deleted_count += cur.rowcount

            # 3. Delete assessment_history
            cur.execute("DELETE FROM assessment_history WHERE patient_id = ?;", (patient_id,))
            deleted_count += cur.rowcount

            # 4. Delete session_audio records
            cur.execute("DELETE FROM session_audio WHERE patient_id = ?;", (patient_id,))
            deleted_count += cur.rowcount

            # 5. Get contact_name for file-based cleanup
            contact_name = (profile.get("chat_name") if profile else None) or patient_id

            # 6. Delete client_profile
            cur.execute("DELETE FROM client_profiles WHERE patient_id = ?;", (patient_id,))
            deleted_count += cur.rowcount

            self.conn.commit()

        # 7. Delete chat files + audio + assessments from disk
        contact_dir = Path(self.db_path).parent / "chats" / contact_name
        if contact_dir.exists():
            try:
                shutil.rmtree(contact_dir)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete contact dir {contact_dir}: {e}")

        # 8. Delete profile photo
        photo_path = profile.get("photo_path")
        if photo_path and Path(photo_path).exists():
            try:
                Path(photo_path).unlink()
            except Exception:
                pass

        # 9. Write tombstone
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO purged_patients (patient_id, purged_at, purged_by, records_deleted) VALUES (?, ?, 'practitioner', ?);",
                (patient_id, now, deleted_count),
            )
            self.conn.commit()

        logger.warning(f"Patient purged: patient_id={patient_id}, records_deleted={deleted_count}")
        return {"status": "purged", "patient_id": patient_id, "purged_at": now, "records_deleted": deleted_count}

    def get_purged_patients(self) -> list[dict]:
        self._ensure_purged_patients_table()
        cur = self.conn.cursor()
        cur.execute("SELECT patient_id, purged_at, purged_by, reason, records_deleted FROM purged_patients ORDER BY purged_at DESC;")
        rows = cur.fetchall()
        return [{"patient_id": r[0], "purged_at": r[1], "purged_by": r[2], "reason": r[3], "records_deleted": r[4]} for r in rows]

    # -------- Contact Platforms (WhatsApp / Instagram) --------

    def record_platform(self, chat_name: str, platform: str, timestamp):
        """Record that a contact has messages from a given platform.
        Timestamp can be epoch ms (int/float), ISO-8601 string, or YYYY-MM-DD.
        """
        date_str = self._resolve_date_str(timestamp)
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO contact_platforms (chat_name, platform, first_seen, last_seen, message_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(chat_name, platform) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    message_count = message_count + 1;
                """,
                (chat_name, platform, date_str, date_str),
            )
            self.conn.commit()

    def get_platforms(self, chat_name: str) -> list[dict]:
        """Return list of platform records for a contact."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT platform, first_seen, last_seen, message_count FROM contact_platforms WHERE chat_name = ?;",
            (chat_name,),
        )
        rows = cur.fetchall()
        return [
            {"platform": r[0], "first_seen": r[1], "last_seen": r[2], "message_count": r[3]}
            for r in rows
        ]

    def get_all_platforms(self) -> dict[str, list[str]]:
        """Return {chat_name: [platform, ...]} for all contacts with platform data."""
        cur = self.conn.cursor()
        cur.execute("SELECT chat_name, platform FROM contact_platforms;")
        result: dict[str, list[str]] = {}
        for chat_name, platform in cur.fetchall():
            result.setdefault(chat_name, []).append(platform)
        return result

    def find_profile_by_whatsapp(self, phone: str) -> dict | None:
        """Find a client profile by WhatsApp phone number.
        Normalizes the phone (strips non-digits) and matches last 8+ digits.
        """
        normalized = re.sub(r"\D", "", phone)
        if len(normalized) < 8:
            return None
        suffix = normalized[-8:]
        self._ensure_client_profiles_table()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT chat_name, display_name, email, mobile, whatsapp, instagram_handle, photo_path, updated_at, patient_id, dob, mrn, consent_active "
            "FROM client_profiles WHERE whatsapp IS NOT NULL;"
        )
        for row in cur.fetchall():
            stored = re.sub(r"\D", "", row[4] or "")
            if stored.endswith(suffix):
                return {
                    "chat_name": row[0],
                    "display_name": row[1],
                    "email": row[2],
                    "mobile": row[3],
                    "whatsapp": row[4],
                    "instagram_handle": row[5],
                    "photo_path": row[6],
                    "updated_at": row[7],
                    "patient_id": row[8],
                    "dob": row[9],
                    "mrn": row[10],
                    "consent_active": bool(row[11]),
                }
        return None

    # -------- Pending Merges --------

    def create_pending_merge(self, new_chat_name: str, existing_chat_name: str, reason: str, similarity: float | None = None,
                             new_client_id: str | None = None, existing_client_id: str | None = None):
        """Insert a pending merge suggestion."""
        now = datetime.now(UTC).isoformat()
        if new_client_id is None:
            new_client_id = self.get_or_create_client_id(new_chat_name)
        if existing_client_id is None:
            existing_client_id = self.get_or_create_client_id(existing_chat_name)
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO pending_merges (new_chat_name, existing_chat_name, new_client_id, existing_client_id, reason, similarity, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending');
                """,
                (new_chat_name, existing_chat_name, new_client_id, existing_client_id, reason, similarity, now),
            )
            self.conn.commit()

    def get_pending_merges(self) -> list[dict]:
        """Return all pending merge suggestions."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT suggestion_id, new_chat_name, existing_chat_name, new_client_id, existing_client_id, reason, similarity, created_at "
                "FROM pending_merges WHERE status = 'pending' ORDER BY created_at DESC;"
            )
            rows = cur.fetchall()
            return [
                {
                    "suggestion_id": r[0],
                    "new_chat_name": r[1],
                    "existing_chat_name": r[2],
                    "new_client_id": r[3],
                    "existing_client_id": r[4],
                    "reason": r[5],
                    "similarity": r[6],
                    "created_at": r[7],
                }
                for r in rows
            ]
        except sqlite3.OperationalError:
            # Fallback for pre-migration schema (no client_id columns yet)
            cur.execute(
                "SELECT suggestion_id, new_chat_name, existing_chat_name, reason, similarity, created_at "
                "FROM pending_merges WHERE status = 'pending' ORDER BY created_at DESC;"
            )
            rows = cur.fetchall()
            return [
                {
                    "suggestion_id": r[0],
                    "new_chat_name": r[1],
                    "existing_chat_name": r[2],
                    "new_client_id": None,
                    "existing_client_id": None,
                    "reason": r[3],
                    "similarity": r[4],
                    "created_at": r[5],
                }
                for r in rows
            ]

    def get_pending_merges_count(self) -> int:
        """Return count of pending merge suggestions."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pending_merges WHERE status = 'pending';")
        return cur.fetchone()[0]

    def dismiss_pending_merge(self, suggestion_id: int):
        """Mark a pending merge as dismissed."""
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute("UPDATE pending_merges SET status = 'dismissed' WHERE suggestion_id = ?;", (suggestion_id,))
            self.conn.commit()

    def mark_pending_merge_merged(self, chat_name: str):
        """Mark all pending merges involving this chat_name as 'merged'."""
        with self._write_lock:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE pending_merges SET status = 'merged' WHERE new_chat_name = ? OR existing_chat_name = ?;",
                (chat_name, chat_name),
            )
            self.conn.commit()
