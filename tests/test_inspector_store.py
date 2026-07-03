"""Unit tests for InspectorStore (JSON-backed, thread-safe)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from src.storage import inspector_store as mod
from src.storage.inspector_store import InspectorStore


@pytest.fixture
def store(tmp_path: Path) -> InspectorStore:
    return InspectorStore(path=tmp_path / "inspector_data.json")


# ----------------------------- Tags ----------------------------- #

def test_get_tags_empty(store: InspectorStore):
    assert store.get_tags("Alice") == []


def test_add_tag_returns_sorted_unique(store: InspectorStore):
    assert store.add_tag("Alice", "client") == ["client"]
    assert store.add_tag("Alice", "  CLIENT  ") == ["client"]  # dedup + lowercase
    assert store.add_tag("Alice", "weekly") == ["client", "weekly"]


def test_add_tag_strips_and_lowercases(store: InspectorStore):
    tags = store.add_tag("Bob", "  FrIEnd  ")
    assert tags == ["friend"]


def test_add_tag_rejects_empty(store: InspectorStore):
    with pytest.raises(ValueError):
        store.add_tag("Alice", "   ")


def test_remove_tag(store: InspectorStore):
    store.add_tag("Alice", "client")
    store.add_tag("Alice", "weekly")
    tags = store.remove_tag("Alice", "client")
    assert tags == ["weekly"]
    # Removing the last tag should drop the contact bucket
    store.remove_tag("Alice", "weekly")
    assert store.get_tags("Alice") == []


def test_remove_tag_missing_is_noop(store: InspectorStore):
    assert store.remove_tag("Alice", "ghost") == []


# ----------------------------- Notes ----------------------------- #

def test_get_notes_empty(store: InspectorStore):
    assert store.get_notes("Alice") == []


def test_add_note_returns_entry(store: InspectorStore):
    note = store.add_note("Alice", "Hello world")
    assert note["note"] == "Hello world"
    assert note["id"]
    assert note["created_at"] == note["updated_at"]


def test_add_note_rejects_empty(store: InspectorStore):
    with pytest.raises(ValueError):
        store.add_note("Alice", "   ")


def test_update_note(store: InspectorStore):
    created = store.add_note("Alice", "original")
    updated = store.update_note("Alice", created["id"], "edited")
    assert updated["note"] == "edited"
    # updated_at should be >= created_at
    assert updated["updated_at"] >= created["updated_at"]


def test_update_note_missing_raises(store: InspectorStore):
    with pytest.raises(KeyError):
        store.update_note("Alice", "no-such-id", "anything")


def test_delete_note(store: InspectorStore):
    a = store.add_note("Alice", "first")
    b = store.add_note("Alice", "second")
    assert store.delete_note("Alice", a["id"]) is True
    remaining = store.get_notes("Alice")
    assert len(remaining) == 1
    assert remaining[0]["id"] == b["id"]


def test_delete_note_missing(store: InspectorStore):
    assert store.delete_note("Alice", "no-such-id") is False


# ----------------------------- Flags ----------------------------- #

def test_get_flags_default(store: InspectorStore):
    assert store.get_flags("Alice") == {"starred": False, "archived": False}


def test_set_flags_toggle(store: InspectorStore):
    flags = store.set_flags("Alice", starred=True)
    assert flags == {"starred": True, "archived": False}
    flags = store.set_flags("Alice", archived=True)
    assert flags == {"starred": True, "archived": True}
    flags = store.set_flags("Alice", starred=False)
    assert flags == {"starred": False, "archived": True}


def test_set_flags_drops_entry_when_both_false(store: InspectorStore):
    store.set_flags("Alice", starred=True)
    store.set_flags("Alice", starred=False)
    # Bucket should be removed, but get_flags should still return defaults
    assert store.get_flags("Alice") == {"starred": False, "archived": False}


def test_set_flags_none_is_noop(store: InspectorStore):
    store.set_flags("Alice", starred=True)
    flags = store.set_flags("Alice")  # both None
    assert flags == {"starred": True, "archived": False}


# ----------------------- Concurrency / atomicity ----------------------- #

def test_concurrent_writes_do_not_corrupt(tmp_path: Path):
    """Spawn N threads each adding tags; final state should contain every tag exactly once."""
    path = tmp_path / "inspector_data.json"
    store = InspectorStore(path=path)

    errors: list[Exception] = []

    def worker(i: int):
        try:
            for j in range(20):
                store.add_tag("Alice", f"tag-{i}-{j}")
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    tags = store.get_tags("Alice")
    assert len(tags) == 8 * 20
    assert len(set(tags)) == 8 * 20


def test_atomic_write_creates_backup(tmp_path: Path):
    path = tmp_path / "inspector_data.json"
    store = InspectorStore(path=path)
    # First write initializes the file; no backup expected yet
    store.add_tag("Alice", "first")
    # Second write should create a backup of the previous file
    store.add_tag("Alice", "second")
    backups = list(tmp_path.glob("inspector_data.backup-*.json"))
    assert len(backups) >= 1
    # Backup files are valid JSON
    for backup in backups:
        doc = json.loads(backup.read_text(encoding="utf-8"))
        assert "tags" in doc


def test_corrupt_file_is_reset(tmp_path: Path):
    path = tmp_path / "inspector_data.json"
    path.write_text("{not json}", encoding="utf-8")
    store = InspectorStore(path=path)
    # Should not raise; should return empty defaults
    assert store.get_tags("Alice") == []


def test_singleton_resets_when_path_changes(tmp_path: Path, monkeypatch):
    """Re-instantiating the module singleton should pick up the new path."""
    monkeypatch.setattr(mod, "_inspector_store", None)
    path1 = tmp_path / "store1.json"
    path2 = tmp_path / "store2.json"
    s1 = InspectorStore(path=path1)
    s1.add_tag("Alice", "alpha")
    s2 = InspectorStore(path=path2)
    assert s2.get_tags("Alice") == []
    assert s1.get_tags("Alice") == ["alpha"]
