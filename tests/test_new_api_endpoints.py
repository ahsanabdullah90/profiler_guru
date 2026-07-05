"""Tests for API endpoints that previously had zero coverage:
- POST /api/v1/contacts/import
- GET /api/v1/contacts/{name}/analytics
- POST /api/v1/rag/search
- GET /api/v1/reports/{name}/download
"""
import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main_api import app
from src.utils.config import config

client = TestClient(app)


def _get_auth_header():
    """Helper: login and return Authorization header dict."""
    resp = client.post("/api/v1/auth/login", json={"password": "koko"})
    if resp.status_code != 200:
        pytest.skip("APP_PASSWORD not configured")
    return {"Authorization": f"Bearer {resp.json()['token']}"}


# ── POST /api/v1/contacts/import ─────────────────────────────────────────

def test_import_empty_path():
    """Import with empty path should return 400."""
    headers = _get_auth_header()
    resp = client.post("/api/v1/contacts/import", json={"path": ""}, headers=headers)
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_import_invalid_path():
    """Import with non-existent path should return 400."""
    headers = _get_auth_header()
    resp = client.post(
        "/api/v1/contacts/import",
        json={"path": "/nonexistent/path/that/does/not/exist"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "does not exist" in resp.json()["detail"].lower()


def test_import_valid_path(tmp_path, monkeypatch):
    """Import with a valid Instagram export structure should return 200 (submitted)."""
    headers = _get_auth_header()
    if not headers:
        pytest.skip("APP_PASSWORD not configured")

    # Create a minimal valid export
    export_dir = tmp_path / "export"
    inbox_dir = export_dir / "messages" / "inbox" / "testuser_123"
    inbox_dir.mkdir(parents=True)
    msg_data = {
        "title": "TestUser",
        "messages": [
            {"sender_name": "TestUser", "timestamp_ms": 1700000000000, "content": "Hello!"}
        ],
    }
    with open(inbox_dir / "message_1.json", "w", encoding="utf-8") as f:
        json.dump(msg_data, f)

    resp = client.post(
        "/api/v1/contacts/import",
        json={"path": str(export_dir)},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "submitted"
    assert "task_id" in data


# ── GET /api/v1/contacts/{name}/analytics ────────────────────────────────

def test_analytics_nonexistent_contact():
    """Analytics for a contact that doesn't exist should return empty data."""
    headers = _get_auth_header()
    resp = client.get("/api/v1/contacts/NonexistentContact999/analytics", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_messages" in data
    assert data["total_messages"] == 0


# ── POST /api/v1/rag/search ──────────────────────────────────────────────

def test_global_search_empty_query():
    """Global search with empty query should return 422 (validation error)."""
    headers = _get_auth_header()
    resp = client.post("/api/v1/rag/search", json={}, headers=headers)
    assert resp.status_code == 422


def test_global_search_returns_results():
    """Global search should return a results list (even if empty)."""
    headers = _get_auth_header()
    resp = client.post(
        "/api/v1/rag/search",
        json={"query": "test query", "n_results": 5},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # Endpoint returns a list of results directly
    assert isinstance(data, list)


# ── GET /api/v1/reports/{name}/download ──────────────────────────────────

def test_download_report_nonexistent():
    """Download for a contact with no report should return 404."""
    headers = _get_auth_header()
    resp = client.get("/api/v1/reports/NonexistentContact999/download", headers=headers)
    assert resp.status_code == 404
