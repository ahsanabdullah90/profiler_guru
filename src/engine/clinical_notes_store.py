"""SQLite-backed clinical notes store for session records.

Replaces the JSON-based InspectorStore notes backend with an auditable
SQLite table. Supports session_date, note_type, consent_version, and
append-only audit (soft-delete + revised_from for edits).

Tags and flags remain in InspectorStore JSON (not clinical data).
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.engine.metrics_engine import MetricsEngine
from src.utils.logger import logger

_me = MetricsEngine()

NOTE_TYPES = frozenset(["free", "soap", "dap", "progress"])


class ClinicalNotesStore:
    """SQLite-backed store for clinical notes with append-only audit."""

    def get_notes(self, contact_name: str) -> list[dict[str, Any]]:
        _me._ensure_clinical_notes_table()
        cur = _me.conn.cursor()
        cur.execute(
            "SELECT note_id, session_date, note_type, note_text, consent_version, created_at, updated_at, revised_from "
            "FROM clinical_notes WHERE contact_name = ? AND deleted_at IS NULL ORDER BY created_at DESC;",
            (contact_name,),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "session_date": r[1],
                "note_type": r[2],
                "note": r[3],
                "consent_version": r[4],
                "created_at": r[5],
                "updated_at": r[6],
                "revised_from": r[7],
            }
            for r in rows
        ]

    def add_note(
        self,
        contact_name: str,
        note_text: str,
        session_date: str | None = None,
        note_type: str = "free",
        consent_version: str | None = None,
    ) -> dict[str, Any]:
        text = note_text.strip()
        if not text:
            raise ValueError("note must be non-empty")
        if note_type not in NOTE_TYPES:
            raise ValueError(f"note_type must be one of: {', '.join(sorted(NOTE_TYPES))}")
        _me._ensure_clinical_notes_table()
        now = datetime.now(UTC).isoformat()
        note_id = str(uuid4())
        ses_date = session_date or now[:10]

        # Resolve patient_id from contact_name
        profile = _me.get_client_profile(contact_name)
        patient_id = profile.get("patient_id", "") if profile else ""

        with _me._write_lock:
            cur = _me.conn.cursor()
            cur.execute(
                "INSERT INTO clinical_notes (note_id, patient_id, contact_name, session_date, note_type, note_text, consent_version, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (note_id, patient_id, contact_name, ses_date, note_type, text, consent_version, now, now),
            )
            _me.conn.commit()

        return {
            "id": note_id,
            "session_date": ses_date,
            "note_type": note_type,
            "note": text,
            "consent_version": consent_version,
            "created_at": now,
            "updated_at": now,
            "revised_from": None,
        }

    def update_note(
        self,
        contact_name: str,
        note_id: str,
        note_text: str,
        session_date: str | None = None,
        note_type: str | None = None,
    ) -> dict[str, Any]:
        text = note_text.strip()
        if not text:
            raise ValueError("note must be non-empty")
        if note_type and note_type not in NOTE_TYPES:
            raise ValueError(f"note_type must be one of: {', '.join(sorted(NOTE_TYPES))}")

        _me._ensure_clinical_notes_table()
        now = datetime.now(UTC).isoformat()
        with _me._write_lock:
            cur = _me.conn.cursor()

            # Fetch existing note
            cur.execute(
                "SELECT note_id, session_date, note_type, note_text, consent_version, created_at "
                "FROM clinical_notes WHERE note_id = ? AND contact_name = ? AND deleted_at IS NULL;",
                (note_id, contact_name),
            )
            existing = cur.fetchone()
            if existing is None:
                raise KeyError(f"note {note_id} not found for contact {contact_name}")

            # Create a new revision (append-only audit)
            new_id = str(uuid4())
            ses_date = session_date if session_date is not None else existing[1]
            new_type = note_type if note_type is not None else existing[2]
            consent_ver = existing[4]  # keep original consent version

            cur.execute(
                "INSERT INTO clinical_notes (note_id, patient_id, contact_name, session_date, note_type, note_text, consent_version, created_at, updated_at, revised_from) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (new_id, _me.get_client_profile(contact_name).get("patient_id", "") if _me.get_client_profile(contact_name) else "",
                 contact_name, ses_date, new_type, text, consent_ver, existing[5], now, note_id),
            )
            # Soft-delete the old revision
            cur.execute(
                "UPDATE clinical_notes SET deleted_at = ? WHERE note_id = ?;",
                (now, note_id),
            )
            _me.conn.commit()

        return {
            "id": new_id,
            "session_date": ses_date,
            "note_type": new_type,
            "note": text,
            "consent_version": consent_ver,
            "created_at": existing[5],
            "updated_at": now,
            "revised_from": note_id,
        }

    def delete_note(self, contact_name: str, note_id: str) -> bool:
        _me._ensure_clinical_notes_table()
        now = datetime.now(UTC).isoformat()
        with _me._write_lock:
            cur = _me.conn.cursor()
            cur.execute(
                "UPDATE clinical_notes SET deleted_at = ? WHERE note_id = ? AND contact_name = ? AND deleted_at IS NULL;",
                (now, note_id, contact_name),
            )
            affected = cur.rowcount
            _me.conn.commit()
        return affected > 0

    def migrate_from_json(self, json_store: Any) -> int:
        """Import notes from the old JSON InspectorStore into SQLite.

        Returns the number of notes migrated.
        """
        _me._ensure_clinical_notes_table()
        count = 0
        # The JSON store stores notes keyed by contact_name
        try:
            doc = json_store._read()
        except Exception as e:
            logger.warning(f"Cannot read JSON store for migration: {e}")
            return 0

        for contact_name, notes in doc.get("notes", {}).items():
            for note in notes:
                note_id = note.get("id", str(uuid4()))
                note_text = note.get("note", "")
                created = note.get("created_at", datetime.now(UTC).isoformat())
                updated = note.get("updated_at", created)

                with _me._write_lock:
                    cur = _me.conn.cursor()
                    # Get patient_id
                    profile = _me.get_client_profile(contact_name)
                    patient_id = profile.get("patient_id", "") if profile else ""
                    cur.execute(
                        "INSERT OR IGNORE INTO clinical_notes (note_id, patient_id, contact_name, session_date, note_type, note_text, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, 'free', ?, ?, ?);",
                        (note_id, patient_id, contact_name, created[:10], note_text, created, updated),
                    )
                    if cur.rowcount > 0:
                        count += 1
                _me.conn.commit()
        return count
