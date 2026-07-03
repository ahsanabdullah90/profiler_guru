"""Thread-safe JSON store for Inspector pane data (tags, notes, flags).

This module is intentionally decoupled from the main SQLite database to
preserve the read-only contract of the existing schema. All writes go
through a single threading.Lock and use atomic temp-file + rename to
prevent corruption on crash or concurrent write.

File location: <DATA_DIR>/inspector_data.json
Backups: <DATA_DIR>/inspector_data.backup-YYYYMMDDTHHMMSS.json (one per write)
"""

from __future__ import annotations

import json
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.utils.config import config
from src.utils.logger import logger


_INSPECTOR_FILE = "inspector_data.json"
_BACKUP_PREFIX = "inspector_data.backup-"
_EMPTY_DOC: dict[str, Any] = {"tags": {}, "notes": {}, "flags": {}}


def _data_path() -> Path:
    return Path(config.DATA_DIR) / _INSPECTOR_FILE


def _backup_path_for(target: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return target.parent / f"{_BACKUP_PREFIX}{ts}.json"


class InspectorStore:
    """JSON-backed store for Inspector data.

    Schema:
        {
            "tags": { "<contact_name>": ["tag1", "tag2", ...], ... },
            "notes": {
                "<contact_name>": [
                    {
                        "id": "<uuid>",
                        "note": "free text",
                        "created_at": "<iso8601>",
                        "updated_at": "<iso8601>",
                    },
                    ...
                ],
                ...
            },
            "flags": {
                "<contact_name>": {"starred": bool, "archived": bool}, ...
            },
        }
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _data_path()
        self._lock = threading.Lock()
        os.makedirs(self._path.parent, exist_ok=True)
        if not self._path.exists():
            self._atomic_write(_EMPTY_DOC)

    # ---------------------------- I/O helpers ---------------------------- #

    def _read(self) -> dict[str, Any]:
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.warning(
                f"Inspector store missing or corrupt at {self._path}: {exc}. Resetting."
            )
            doc = dict(_EMPTY_DOC)
            self._atomic_write(doc)
        if not isinstance(doc, dict):
            doc = dict(_EMPTY_DOC)
        doc.setdefault("tags", {})
        doc.setdefault("notes", {})
        doc.setdefault("flags", {})
        return doc

    def _atomic_write(self, doc: dict[str, Any]) -> None:
        """Write to a temp file, fsync, then atomic-rename over the target.

        Also creates a single timestamped backup of the previous file when
        one exists.
        """
        os.makedirs(self._path.parent, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        if self._path.exists():
            try:
                shutil.copy2(self._path, _backup_path_for(self._path))
            except OSError as exc:
                logger.warning(f"Inspector backup failed: {exc}")
        os.replace(tmp, self._path)

    # ------------------------------- Tags ------------------------------- #

    def get_tags(self, contact: str) -> list[str]:
        with self._lock:
            doc = self._read()
        return sorted(set(doc["tags"].get(contact, [])))

    def add_tag(self, contact: str, tag: str) -> list[str]:
        tag_clean = tag.strip().lower()
        if not tag_clean:
            raise ValueError("tag must be non-empty")
        with self._lock:
            doc = self._read()
            bucket = doc["tags"].setdefault(contact, [])
            if tag_clean not in bucket:
                bucket.append(tag_clean)
                self._atomic_write(doc)
            return sorted(set(doc["tags"].get(contact, [])))

    def remove_tag(self, contact: str, tag: str) -> list[str]:
        tag_clean = tag.strip().lower()
        with self._lock:
            doc = self._read()
            bucket = doc["tags"].get(contact, [])
            if tag_clean in bucket:
                bucket = [t for t in bucket if t != tag_clean]
                if bucket:
                    doc["tags"][contact] = bucket
                else:
                    doc["tags"].pop(contact, None)
                self._atomic_write(doc)
            return sorted(set(doc["tags"].get(contact, [])))

    # ------------------------------ Notes ------------------------------ #

    def get_notes(self, contact: str) -> list[dict[str, Any]]:
        with self._lock:
            doc = self._read()
        notes = doc["notes"].get(contact, [])
        return sorted(notes, key=lambda n: n.get("created_at", ""), reverse=True)

    def add_note(self, contact: str, note_text: str) -> dict[str, Any]:
        text = note_text.strip()
        if not text:
            raise ValueError("note must be non-empty")
        now = datetime.now(timezone.utc).isoformat()
        new_note = {
            "id": str(uuid4()),
            "note": text,
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            doc = self._read()
            doc["notes"].setdefault(contact, []).append(new_note)
            self._atomic_write(doc)
        return new_note

    def update_note(self, contact: str, note_id: str, note_text: str) -> dict[str, Any]:
        text = note_text.strip()
        if not text:
            raise ValueError("note must be non-empty")
        with self._lock:
            doc = self._read()
            notes = doc["notes"].get(contact, [])
            target = next((n for n in notes if n.get("id") == note_id), None)
            if target is None:
                raise KeyError(f"note {note_id} not found for contact {contact}")
            target["note"] = text
            target["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._atomic_write(doc)
        return target

    def delete_note(self, contact: str, note_id: str) -> bool:
        with self._lock:
            doc = self._read()
            notes = doc["notes"].get(contact, [])
            new_notes = [n for n in notes if n.get("id") != note_id]
            if len(new_notes) == len(notes):
                return False
            if new_notes:
                doc["notes"][contact] = new_notes
            else:
                doc["notes"].pop(contact, None)
            self._atomic_write(doc)
        return True

    # ------------------------------ Flags ------------------------------ #

    def get_flags(self, contact: str) -> dict[str, bool]:
        with self._lock:
            doc = self._read()
        raw = doc["flags"].get(contact, {})
        return {
            "starred": bool(raw.get("starred", False)),
            "archived": bool(raw.get("archived", False)),
        }

    def set_flags(
        self,
        contact: str,
        starred: bool | None = None,
        archived: bool | None = None,
    ) -> dict[str, bool]:
        with self._lock:
            doc = self._read()
            current = doc["flags"].setdefault(contact, {"starred": False, "archived": False})
            if starred is not None:
                current["starred"] = bool(starred)
            if archived is not None:
                current["archived"] = bool(archived)
            if not current["starred"] and not current["archived"]:
                doc["flags"].pop(contact, None)
            else:
                doc["flags"][contact] = current
            self._atomic_write(doc)
        return {
            "starred": bool(current.get("starred", False)),
            "archived": bool(current.get("archived", False)),
        }


# Module-level singleton, lazily instantiated.
_inspector_store: InspectorStore | None = None


def get_inspector_store() -> InspectorStore:
    global _inspector_store
    if _inspector_store is None:
        _inspector_store = InspectorStore()
    return _inspector_store
