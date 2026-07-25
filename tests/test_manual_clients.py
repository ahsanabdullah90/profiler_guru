import pytest
import uuid
from fastapi.testclient import TestClient
from main_api import app
from src.engine.metrics_engine import MetricsEngine

client = TestClient(app)


def _get_auth_header():
    """Helper: login with APP_PASSWORD and return Authorization header dict."""
    resp = client.post("/api/v1/auth/login", json={"password": "koko"})
    if resp.status_code != 200:
        pytest.skip("APP_PASSWORD not configured")
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def test_manual_client_lifecycle():
    """Test manual client creation, duplicate name collision handling, and listing."""
    headers = _get_auth_header()

    # 1. Reject empty display name
    resp = client.post("/api/v1/contacts", json={"display_name": "   "}, headers=headers)
    assert resp.status_code == 400
    assert "required" in resp.json()["detail"]

    # 2. Create happy path
    unique_name = f"Jane Test {uuid.uuid4().hex[:6]}"
    payload = {
        "display_name": unique_name,
        "email": "jane.test@example.com",
        "mobile": "+15559988",
        "whatsapp": "+15559988",
        "instagram_handle": "jane_test_insta",
        "dob": "1990-05-15",
        "national_id": "SSN-123-456",
    }
    resp = client.post("/api/v1/contacts", json=payload, headers=headers)
    assert resp.status_code == 201
    created_data = resp.json()
    assert "chat_name" in created_data
    assert created_data["display_name"] == unique_name
    assert created_data["source"] == "manual"
    assert len(created_data["patient_id"]) == 12

    chat_name = created_data["chat_name"]

    # 3. Verify in database directly
    me = MetricsEngine()
    profile = me.get_client_profile(chat_name)
    assert profile is not None
    assert profile["display_name"] == unique_name
    assert profile["source"] == "manual"
    assert profile["patient_id"] == created_data["patient_id"]
    assert profile["dob"] == "1990-05-15"
    assert profile["national_id"] == "SSN-123-456"

    # Verify contact_metadata is created
    meta = me.get_contact_metadata(chat_name)
    assert meta is not None
    assert meta["message_count"] == 0
    assert meta["last_snippet"] == "Manually created client."

    # 4. Collision loop check: POST again with same display name should succeed with a different chat_name
    resp_dup = client.post("/api/v1/contacts", json=payload, headers=headers)
    assert resp_dup.status_code == 201
    dup_data = resp_dup.json()
    assert dup_data["chat_name"] != chat_name
    assert dup_data["display_name"] == unique_name


def test_manual_client_merge():
    """Verify merge of imported contact into manual client preserves profile details and reassigns clinical data."""
    headers = _get_auth_header()

    # Create a manual client (primary)
    me = MetricsEngine()
    manual_display = f"Merge Test {uuid.uuid4().hex[:6]}"
    resp_manual = client.post(
        "/api/v1/contacts",
        json={"display_name": manual_display, "email": "primary@test.com", "dob": "1988-08-08"},
        headers=headers,
    )
    assert resp_manual.status_code == 201
    primary_name = resp_manual.json()["chat_name"]
    primary_profile = me.get_client_profile(primary_name)
    patient_id = primary_profile["patient_id"]

    # Add clinical note to primary manual client
    with me._write_lock:
        me.conn.execute(
            "INSERT INTO clinical_notes (note_id, patient_id, contact_name, session_date, note_text, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("note_123_test", patient_id, primary_name, "2026-07-18", "Original manual client note.", "2026-07-18", "2026-07-18"),
        )
        # Create secondary imported contact
        secondary_name = f"secondary_import_{uuid.uuid4().hex[:6]}"
        me.conn.execute(
            "INSERT INTO client_profiles (chat_name, client_id, canonical_name, display_name, dob, source) VALUES (?, ?, ?, ?, ?, 'import')",
            (secondary_name, secondary_name, secondary_name, "Secondary Import", "1988-08-08"),
        )
        me.conn.execute(
            "INSERT INTO contact_metadata (chat_name, message_count, last_snippet, last_date) VALUES (?, 10, 'Last import msg', '2026-07-10')",
            (secondary_name,),
        )
        me.conn.commit()

    # Trigger contact merge
    merge_payload = {
        "primary_chat_name": primary_name,
        "secondary_chat_name": secondary_name,
        "password": "koko",
    }
    resp_merge = client.post("/api/v1/contacts/merge", json=merge_payload, headers=headers)
    assert resp_merge.status_code == 200

    # Verify primary remains and profile is updated/reassigned
    merged_profile = me.get_client_profile(primary_name)
    assert merged_profile is not None
    assert merged_profile["display_name"] == manual_display
    assert merged_profile["email"] == "primary@test.com"
    assert merged_profile["dob"] == "1988-08-08"

    # Verify secondary deleted
    assert me.get_client_profile(secondary_name) is None
    assert me.get_contact_metadata(secondary_name) is None

    # Clean up test note
    with me._write_lock:
        me.conn.execute("DELETE FROM clinical_notes WHERE note_id = ?", ("note_123_test",))
        me.conn.commit()
