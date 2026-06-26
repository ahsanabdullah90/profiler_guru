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


def test_unauthenticated_access_returns_401():
    """Protected endpoints without a token should return 401."""
    endpoints = [
        ("GET", "/api/v1/contacts"),
        ("GET", "/api/v1/settings"),
        ("GET", "/api/v1/instagram/status"),
        ("POST", "/api/v1/rag/search"),
        ("POST", "/api/v1/rag/contacts/test/profile"),
        ("GET", "/api/v1/reports/contacts/test/download"),
    ]
    for method, path in endpoints:
        response = client.request(method, path)
        assert response.status_code == 401, f"{method} {path} should return 401"


def test_unauthenticated_audio_access_returns_401():
    """Verify that unauthenticated access to the audio endpoint returns 401."""
    response = client.get("/static/audio/test_contact/test_file.mp3")
    assert response.status_code == 401


def test_unauthenticated_rag_access_returns_401():
    """Verify that RAG endpoints return 401 when unauthenticated."""
    response = client.post("/api/v1/rag/contacts/test_contact/query", json={"query": "hello"})
    assert response.status_code == 401


def test_path_traversal_returns_400():
    """Verify that path traversal or invalid characters in names return 400 or are safely rejected with 404."""
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    # Invalid names that match the route but fail regex validation
    invalid_names = ["contact$name", "contact<script>", "a" * 105]
    for name in invalid_names:
        response = client.get(f"/api/v1/contacts/{name}/months", headers=headers)
        assert response.status_code == 400

    # Path traversal attempts with directory markers result in 404 because
    # the router resolves them to non-existent paths, which is also a safe rejection.
    for name in ["../test", "test/.."]:
        response = client.get(f"/api/v1/contacts/{name}/months", headers=headers)
        assert response.status_code in (400, 404)


def test_message_sanitization_escapes_html(tmp_path, monkeypatch):
    """Verify that HTML characters in messages are escaped server-side."""
    # Mock config.CHATS_DIR to a temporary folder
    chats_dir = tmp_path / "chats"
    contact_dir = chats_dir / "test_user"
    chats_sub_dir = contact_dir / "Chats"
    chats_sub_dir.mkdir(parents=True, exist_ok=True)
    
    # Write a mock chat file with HTML tags
    chat_file = chats_sub_dir / "2026-06.md"
    chat_content = """### [18:30] sender_name
This is a <script>alert('XSS')</script> message with <b>HTML</b>.
"""
    chat_file.write_text(chat_content, encoding="utf-8")
    
    # Patch config.CHATS_DIR
    monkeypatch.setattr(config, "CHATS_DIR", str(chats_dir))
    
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    response = client.get("/api/v1/contacts/test_user/messages/2026-06.md", headers=headers)
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) > 0
    msg = messages[0]
    # The script and b tags should be escaped
    assert "<script>" not in msg["text"]
    assert "<b>" not in msg["text"]
    assert "&lt;script&gt;" in msg["text"]
    assert "&lt;b&gt;" in msg["text"]


def test_idempotency_middleware():
    """Verify that sending duplicate requests with the same Idempotency-Key returns cached response."""
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    headers_with_key = headers.copy()
    headers_with_key["Idempotency-Key"] = "test-unique-key-12345"

    # First request
    response1 = client.post(
        "/api/v1/settings",
        json={"settings": {"test_key": "val1"}},
        headers=headers_with_key,
    )
    assert response1.status_code == 200
    body1 = response1.json()

    # Second request with same key
    response2 = client.post(
        "/api/v1/settings",
        json={"settings": {"test_key": "val2"}},
        headers=headers_with_key,
    )
    assert response2.status_code == 200
    assert response2.headers.get("X-Cache-Lookup") == "HIT"
    body2 = response2.json()

    # The cached response body should match the first response (val1, not val2!)
    assert body1 == body2


def test_rate_limiting(monkeypatch):
    """Verify that hitting the RAG query endpoint in rapid succession triggers a 429 error."""
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    # Mock LLM dispatch to return instantly to avoid slow Ollama network retries
    from src.engine.llm_dispatcher import llm_dispatcher
    monkeypatch.setattr(llm_dispatcher, "dispatch", lambda *args, **kwargs: "Mock response")

    # Clear rate limiter history to start clean
    from src.api.api_rag import rag_rate_limiter
    rag_rate_limiter.history.clear()

    # Perform 10 successful requests (or up to limit)
    for i in range(10):
        resp = client.post(
            "/api/v1/rag/contacts/test/query",
            json={"query": "test query"},
            headers=headers
        )
        assert resp.status_code == 200

    # The 11th request must trigger the rate limiter and return 429
    resp_limit = client.post(
        "/api/v1/rag/contacts/test/query",
        json={"query": "test query"},
        headers=headers
    )
    assert resp_limit.status_code == 429
    assert "Rate limit exceeded" in resp_limit.json()["detail"]


def test_async_pdf_reports(monkeypatch):
    """Verify that PDF generation runs in the background and status can be polled."""
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    from pathlib import Path
    
    # Mock the heavy PDF generation call to write a dummy file so exists() returns true
    from src.engine.report_generator import report_generator
    def mock_create_pdf(contact, start_month, end_month, content, settings, out_path):
        out_path.write_text("Mock PDF content", encoding="utf-8")
        
    monkeypatch.setattr(report_generator, "create_assessment_pdf", mock_create_pdf)

    # Trigger generation
    payload = {
        "start_month": "2026-05",
        "end_month": "2026-06",
        "profile_text": "Mock profile text content."
    }
    resp = client.post(
        "/api/v1/reports/contacts/test/generate",
        json=payload,
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "generating"
    assert "test_personality_report.pdf" in data["filename"]

    # Immediately poll status
    status_resp = client.get("/api/v1/reports/contacts/test/generate/status", headers=headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] in ("generating", "completed")

    # Clean up the created mock PDF file
    pdf_path = Path(config.EXPORTS_DIR) / "test_personality_report.pdf"
    if pdf_path.exists():
        pdf_path.unlink()


def test_structured_llm_error(monkeypatch):
    """Verify that LLM dispatcher failures return a structured HTTP 502 response."""
    headers = _get_auth_header()
    if headers is None:
        pytest.skip("APP_PASSWORD not configured")

    # Clear rate limiter history to start clean and prevent 429 from previous tests
    from src.api.api_rag import rag_rate_limiter
    rag_rate_limiter.history.clear()

    from src.engine.llm_dispatcher import llm_dispatcher, LLMDispatchError
    
    # Mock dispatch to raise LLMDispatchError
    def mock_dispatch_error(*args, **kwargs):
        raise LLMDispatchError("Simulated LLM service interruption.")
        
    monkeypatch.setattr(llm_dispatcher, "dispatch", mock_dispatch_error)

    resp = client.post(
        "/api/v1/rag/contacts/test/query",
        json={"query": "test query"},
        headers=headers
    )
    # Should catch LLMDispatchError and return 502 Bad Gateway
    assert resp.status_code == 502
    data = resp.json()
    assert "detail" in data
    assert data["detail"]["error"] == "LLM_DISPATCH_FAILED"
    assert "Simulated LLM service interruption" in data["detail"]["message"]
    assert data["detail"]["can_retry"] is True

