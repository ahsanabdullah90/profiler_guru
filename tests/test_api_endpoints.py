import pytest
from fastapi.testclient import TestClient
from main_api import app
from src.utils.config import config

client = TestClient(app)

def test_auth_login_invalid():
    """Verify that invalid password returns 401 Unauthorized."""
    response = client.post("/api/auth/login", json={"password": "wrong_password_12345"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect password"}

def test_instagram_status():
    """Verify that the Instagram status endpoint returns the expected schema keys."""
    response = client.get("/api/instagram/status")
    assert response.status_code == 200
    data = response.json()
    assert "logged_in" in data
    assert "username" in data
    assert "active_syncs" in data
    assert "daemon_sync_active" in data
    assert "challenge_url" in data

def test_contacts_endpoint():
    """Verify that the contacts list endpoint returns 200 and a list structure."""
    response = client.get("/api/contacts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        contact = data[0]
        assert "name" in contact
        assert "msg_count" in contact
        assert "last_date" in contact
        assert "last_snippet" in contact
        assert "avg_msg" in contact
        assert "indexed_chunks" in contact
        assert "rag_progress" in contact

def test_settings_endpoint():
    """Verify that settings can be retrieved and contain essential configuration keys."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "settings" in data
    assert "installed_ollama_models" in data
    assert "best_local_model" in data
    assert "has_google_key" in data

def test_health_endpoint():
    """Verify that the health check endpoint returns 200 and a status 'ok'."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data

