import pytest
from fastapi.testclient import TestClient
from main_api import app
from src.utils.config import config

client = TestClient(app)


def _get_auth_header():
    """Helper: login with APP_PASSWORD and return Authorization header dict."""
    pw = config.APP_PASSWORD or "test_password"
    resp = client.post("/api/v1/auth/login", json={"password": pw})
    if resp.status_code == 401:
        # No password configured — tests that require auth will be skipped
        return None
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    """Health check is always public."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_auth_login_invalid():
    """Verify that invalid password returns 401 Unauthorized."""
    response = client.post("/api/v1/auth/login", json={"password": "wrong_password_12345"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect password"}


def test_auth_login_no_password_configured():
    """When APP_PASSWORD is not set, login should return 500."""
    saved = config.APP_PASSWORD
    config.APP_PASSWORD = None
    try:
        response = client.post("/api/v1/auth/login", json={"password": "anything"})
        assert response.status_code == 500
    finally:
        config.APP_PASSWORD = saved


def test_auth_verify_valid_token():
    """A valid JWT should pass /auth/verify."""
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    response = client.get("/api/v1/auth/verify", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "valid"}


def test_auth_verify_no_token():
    """Missing token on a protected endpoint returns 401."""
    response = client.get("/api/v1/auth/verify")
    assert response.status_code == 401


def test_auth_refresh():
    """Token refresh should return a new valid token."""
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    response = client.post("/api/v1/auth/refresh", headers=headers)
    assert response.status_code == 200
    assert "token" in response.json()

    # The new token should also be valid
    new_token = response.json()["token"]
    verify_resp = client.get(
        "/api/v1/auth/verify",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert verify_resp.status_code == 200


def test_legacy_redirect_login():
    """Legacy /api/auth/login should redirect (307) to /api/v1/auth/login."""
    response = client.post("/api/auth/login", json={"password": "anything"}, follow_redirects=False)
    assert response.status_code == 307
    assert "/api/v1/auth/login" in response.headers.get("location", "")


def test_instagram_status():
    """The Instagram status endpoint returns expected keys."""
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    response = client.get("/api/v1/instagram/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "logged_in" in data
    assert "username" in data
    assert "active_syncs" in data
    assert "daemon_sync_active" in data
    assert "challenge_url" in data


def test_contacts_endpoint():
    """Contacts list endpoint returns 200 and a list."""
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    response = client.get("/api/v1/contacts", headers=headers)
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
    """Settings endpoint returns 200 with configuration keys."""
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    response = client.get("/api/v1/settings", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "settings" in data
    assert "installed_ollama_models" in data
    assert "best_local_model" in data
    assert "has_google_key" in data


def test_unauthenticated_access_returns_401():
    """Protected endpoints without a token should return 401."""
    endpoints = [
        ("GET", "/api/v1/contacts"),
        ("GET", "/api/v1/settings"),
        ("GET", "/api/v1/instagram/status"),
    ]
    for method, path in endpoints:
        response = client.request(method, path)
        assert response.status_code == 401, f"{method} {path} should return 401"
