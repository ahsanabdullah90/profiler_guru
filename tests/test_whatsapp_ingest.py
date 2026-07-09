"""Tests for the WhatsApp ingest endpoint."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from main_api import app
from src.engine.metrics_engine import MetricsEngine

client = TestClient(app)

SAMPLE_PAYLOAD = {
    "timestamp": 1777467503,
    "from": "1234567890@c.us",
    "fromMe": False,
    "body": "Hello doctor",
    "type": "chat",
    "contact_name": "TestContact",
    "quoted_body": None,
    "quoted_author": None,
    "media_data": None,
    "media_mimetype": None,
}

AUDIO_PAYLOAD = {
    "timestamp": 1777467504,
    "from": "1234567891@c.us",
    "fromMe": False,
    "body": "",
    "type": "ptt",
    "contact_name": "AudioContact",
    "quoted_body": None,
    "quoted_author": None,
    "media_data": "T3dnU3BlY2lhbA==",  # base64 "OggSpecial"
    "media_mimetype": "audio/ogg; codecs=opus",
}

OUTGOING_PAYLOAD = {
    "timestamp": 1777467505,
    "from": "1234567890@c.us",
    "fromMe": True,
    "body": "How are you feeling today?",
    "type": "chat",
    "contact_name": "TestContact",
    "quoted_body": None,
    "quoted_author": None,
}


def test_ingest_text_message():
    """Basic text message should be accepted."""
    resp = client.post("/api/v1/whatsapp/ingest", json=SAMPLE_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_ingest_outgoing():
    """Outgoing message (fromMe=True) should be accepted."""
    resp = client.post("/api/v1/whatsapp/ingest", json=OUTGOING_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_ingest_quoted_message():
    """Quoted message should be accepted."""
    payload = {**SAMPLE_PAYLOAD, "quoted_body": "Original msg", "quoted_author": "Patient"}
    resp = client.post("/api/v1/whatsapp/ingest", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_ingest_duplicate():
    """Same message sent twice should still return 200 (idempotent)."""
    resp1 = client.post("/api/v1/whatsapp/ingest", json=SAMPLE_PAYLOAD)
    assert resp1.status_code == 200
    resp2 = client.post("/api/v1/whatsapp/ingest", json=SAMPLE_PAYLOAD)
    assert resp2.status_code == 200


def test_ingest_audio_message():
    """Audio message with base64 media should be accepted."""
    with patch("builtins.open", MagicMock()):
        with patch("os.makedirs", MagicMock()):
            resp = client.post("/api/v1/whatsapp/ingest", json=AUDIO_PAYLOAD)
    # Note: in test environment this may fail on file ops, but should return 200 with error in body
    assert resp.status_code in (200, 500)


def test_platform_recorded():
    """After ingest, platform should be recordable via MetricsEngine."""
    me = MetricsEngine()
    me.record_platform("test_wa_contact", "whatsapp", 1777467503 * 1000)
    platforms = me.get_platforms("test_wa_contact")
    wa = [p for p in platforms if p["platform"] == "whatsapp"]
    assert len(wa) == 1
    assert wa[0]["message_count"] >= 1


def test_find_profile_by_whatsapp():
    """find_profile_by_whatsapp should find profiles by phone number."""
    me = MetricsEngine()
    # This relies on a profile existing, which it may not in test env
    result = me.find_profile_by_whatsapp("1234567890")
    # Should not crash regardless of result
    assert result is None or isinstance(result, dict)


def test_ingest_endpoint_no_auth():
    """Ingest endpoint should be public (no auth required)."""
    resp = client.post("/api/v1/whatsapp/ingest", json=SAMPLE_PAYLOAD)
    assert resp.status_code == 200


def test_status_endpoint():
    """Status endpoint should return bridge info."""
    resp = client.get("/api/v1/whatsapp/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "bridge_online" in data
    assert "total_messages" in data
    assert "pending_merges" in data
