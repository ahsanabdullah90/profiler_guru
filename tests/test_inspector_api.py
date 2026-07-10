"""Integration tests for the Inspector API (tags, notes, flags)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main_api import app


client = TestClient(app)


@pytest.fixture
def auth_headers():
    resp = client.post("/api/v1/auth/login", json={"password": "koko"})
    if resp.status_code != 200:
        pytest.skip("APP_PASSWORD not configured")
    return {"Authorization": f"Bearer {resp.json()['token']}"}


@pytest.fixture
def tmp_inspector_path(tmp_path: Path, monkeypatch):
    """Redirect InspectorStore to a temp file and reset the singleton."""
    from src.storage import inspector_store as mod
    target = tmp_path / "inspector_data.json"
    store = mod.InspectorStore(path=target)
    monkeypatch.setattr(mod, "_inspector_store", store)
    yield target
    # Clean up any backup files
    for f in tmp_path.glob("inspector_data.backup-*.json"):
        try:
            os.remove(f)
        except OSError:
            pass


# ----------------------------- Tags ----------------------------- #

def test_tag_lifecycle(tmp_inspector_path, auth_headers):
    r = client.get("/api/v1/inspector/Alice/tags", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"contact": "Alice", "tags": []}

    r = client.post(
        "/api/v1/inspector/Alice/tags",
        headers=auth_headers,
        json={"tag": "client"},
    )
    assert r.status_code == 200
    assert r.json()["tags"] == ["client"]

    r = client.post(
        "/api/v1/inspector/Alice/tags",
        headers=auth_headers,
        json={"tag": "  CLIENT  "},  # dedup
    )
    assert r.json()["tags"] == ["client"]

    r = client.delete(
        "/api/v1/inspector/Alice/tags/client",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["tags"] == []


def test_tag_empty_rejected(tmp_inspector_path, auth_headers):
    r = client.post(
        "/api/v1/inspector/Alice/tags",
        headers=auth_headers,
        json={"tag": "   "},
    )
    assert r.status_code == 400


def test_tag_requires_auth(tmp_inspector_path):
    r = client.get("/api/v1/inspector/Alice/tags")
    assert r.status_code == 401


# ----------------------------- Notes ----------------------------- #

def test_note_lifecycle(tmp_inspector_path, auth_headers):
    r = client.get("/api/v1/inspector/Alice/notes", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["notes"] == []

    r = client.post(
        "/api/v1/inspector/Alice/notes",
        headers=auth_headers,
        json={"note": "First observation"},
    )
    assert r.status_code == 201
    note = r.json()
    assert note["note"] == "First observation"
    note_id = note["id"]

    r = client.put(
        f"/api/v1/inspector/Alice/notes/{note_id}",
        headers=auth_headers,
        json={"note": "Edited observation"},
    )
    assert r.status_code == 200
    updated_note = r.json()
    assert updated_note["note"] == "Edited observation"
    new_note_id = updated_note["id"]

    r = client.delete(
        f"/api/v1/inspector/Alice/notes/{new_note_id}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json() == {"deleted": True, "note_id": new_note_id}

    r = client.get("/api/v1/inspector/Alice/notes", headers=auth_headers)
    assert r.json()["notes"] == []


def test_note_update_missing_returns_404(tmp_inspector_path, auth_headers):
    r = client.put(
        "/api/v1/inspector/Alice/notes/no-such-id",
        headers=auth_headers,
        json={"note": "anything"},
    )
    assert r.status_code == 404


def test_note_delete_missing_returns_false(tmp_inspector_path, auth_headers):
    r = client.delete(
        "/api/v1/inspector/Alice/notes/no-such-id",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json() == {"deleted": False, "note_id": "no-such-id"}


# ----------------------------- Flags ----------------------------- #

def test_flags_default(tmp_inspector_path, auth_headers):
    r = client.get("/api/v1/inspector/Alice/flags", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"contact": "Alice", "starred": False, "archived": False}


def test_flags_patch(tmp_inspector_path, auth_headers):
    r = client.patch(
        "/api/v1/inspector/Alice/flags",
        headers=auth_headers,
        json={"starred": True},
    )
    assert r.status_code == 200
    assert r.json() == {"contact": "Alice", "starred": True, "archived": False}

    r = client.patch(
        "/api/v1/inspector/Alice/flags",
        headers=auth_headers,
        json={"archived": True},
    )
    assert r.json() == {"contact": "Alice", "starred": True, "archived": True}

    r = client.patch(
        "/api/v1/inspector/Alice/flags",
        headers=auth_headers,
        json={"starred": False, "archived": False},
    )
    assert r.json() == {"contact": "Alice", "starred": False, "archived": False}
