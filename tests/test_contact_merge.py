import pytest
from unittest.mock import MagicMock, patch

_mock_rag = MagicMock()
_mock_rag.delete_vectors_by_contact = MagicMock()
_mock_rag.add_messages_batch = MagicMock()

_mock_rag_module = MagicMock()
_mock_rag_module.rag_engine = _mock_rag

@pytest.fixture(autouse=True, scope="module")
def _patch_rag_engine():
    _patcher = patch.dict("sys.modules", {"src.engine.rag_engine": _mock_rag_module})
    _patcher.start()
    yield
    _patcher.stop()

from src.engine.metrics_engine import MetricsEngine
from src.services.contact_merge import merge_contacts


def _cleanup_contact(name: str):
    me = MetricsEngine()
    with me._write_lock:
        cur = me.conn.cursor()
        for table in (
            "contact_metadata", "connection_metrics", "contact_platforms",
            "client_profiles", "pending_merges",
        ):
            try:
                cur.execute(f"DELETE FROM {table} WHERE chat_name = ?;", (name,))
            except Exception:
                pass
        me.conn.commit()


def _ensure_merge_tables():
    """Ensure all tables that merge_contacts accesses exist."""
    me = MetricsEngine()
    me._ensure_client_profiles_table()
    me._ensure_patient_consents_table()
    me._ensure_clinical_notes_table()
    # Ensure assessment_history and session_audio exist
    for _table, create_sql in [
        ("assessment_history", "CREATE TABLE IF NOT EXISTS assessment_history (history_id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, contact_name TEXT, framework_id TEXT, generated_at TEXT);"),
        ("session_audio", "CREATE TABLE IF NOT EXISTS session_audio (session_id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, audio_path TEXT, uploaded_at TEXT);"),
    ]:
        try:
            me.conn.execute(create_sql)
            me.conn.commit()
        except Exception:
            pass


def test_merge_self_rejected():
    result = merge_contacts("same_contact", "same_contact")
    assert "error" in result


def test_merge_contact_metadata_summed():
    me = MetricsEngine()
    primary = "merge_meta_primary"
    secondary = "merge_meta_secondary"
    _cleanup_contact(primary)
    _cleanup_contact(secondary)

    me.increment_message(primary, 1777467503000)
    me.increment_message(primary, 1777467504000)
    me.increment_message(secondary, 1777467505000)

    with patch("src.services.contact_merge.Path.exists", return_value=False):
        with patch("src.services.contact_merge.shutil.rmtree", MagicMock()):
            merge_contacts(primary, secondary)

    meta = me.get_contact_metadata(primary)
    assert meta is not None
    assert meta["message_count"] >= 3
    meta2 = me.get_contact_metadata(secondary)
    assert meta2 is None


def test_merge_connection_metrics_summed():
    me = MetricsEngine()
    primary = "merge_cm_primary"
    secondary = "merge_cm_secondary"
    _cleanup_contact(primary)
    _cleanup_contact(secondary)

    me.increment_message(primary, 1777467503000)
    me.increment_message(secondary, 1777467505000)

    with patch("src.services.contact_merge.Path.exists", return_value=False):
        with patch("src.services.contact_merge.shutil.rmtree", MagicMock()):
            merge_contacts(primary, secondary)

    cur = me.conn.cursor()
    cur.execute(
        "SELECT SUM(message_count) FROM connection_metrics WHERE chat_name = ?;",
        (primary,),
    )
    row = cur.fetchone()
    assert row is not None
    assert row[0] >= 2


def test_merge_platforms_combined():
    me = MetricsEngine()
    primary = "merge_pl_primary"
    secondary = "merge_pl_secondary"
    _cleanup_contact(primary)
    _cleanup_contact(secondary)

    me.record_platform(primary, "instagram", 1777467503000)
    me.record_platform(secondary, "whatsapp", 1777467505000)
    me.increment_message(primary, 1777467503000)
    me.increment_message(secondary, 1777467505000)

    with patch("src.services.contact_merge.Path.exists", return_value=False):
        with patch("src.services.contact_merge.shutil.rmtree", MagicMock()):
            merge_contacts(primary, secondary)

    platforms = me.get_platforms(primary)
    platform_names = [p["platform"] for p in platforms]
    assert "instagram" in platform_names
    assert "whatsapp" in platform_names


def test_merge_client_profiles_merged():
    me = MetricsEngine()
    primary = "merge_prof_primary"
    secondary = "merge_prof_secondary"
    _cleanup_contact(primary)
    _cleanup_contact(secondary)
    _ensure_merge_tables()

    me.upsert_client_profile(primary, display_name="Primary Name", email="primary@test.com")
    me.upsert_client_profile(secondary, display_name="Secondary Name", whatsapp="+1234567890")
    me.increment_message(primary, 1777467503000)
    me.increment_message(secondary, 1777467505000)

    with patch("src.services.contact_merge.Path.exists", return_value=False):
        with patch("src.services.contact_merge.shutil.rmtree", MagicMock()):
            merge_contacts(primary, secondary)

    profile = me.get_client_profile(primary)
    assert profile is not None
    assert profile["display_name"] == "Primary Name"
    assert profile["whatsapp"] == "+1234567890"
    assert me.get_client_profile(secondary) is None


def test_merge_rag_vectors_deleted():
    me = MetricsEngine()
    primary = "merge_rag_primary"
    secondary = "merge_rag_secondary"
    _cleanup_contact(primary)
    _cleanup_contact(secondary)
    me.increment_message(primary, 1777467503000)
    me.increment_message(secondary, 1777467505000)

    with patch("src.services.contact_merge.Path.exists", return_value=False):
        with patch("src.services.contact_merge.shutil.rmtree", MagicMock()):
            merge_contacts(primary, secondary)

    _mock_rag.delete_vectors_by_contact.assert_called()


def test_merge_pending_merges_marked():
    me = MetricsEngine()
    primary = "merge_pm_primary"
    secondary = "merge_pm_secondary"
    _cleanup_contact(primary)
    _cleanup_contact(secondary)

    me.create_pending_merge(secondary, primary, "test suggestion", 0.85)
    me.increment_message(primary, 1777467503000)
    me.increment_message(secondary, 1777467505000)

    with patch("src.services.contact_merge.Path.exists", return_value=False):
        with patch("src.services.contact_merge.shutil.rmtree", MagicMock()):
            merge_contacts(primary, secondary)

    remaining = me.get_pending_merges()
    matching = [p for p in remaining if p["new_chat_name"] == secondary]
    assert len(matching) == 0


def test_merge_idempotent():
    me = MetricsEngine()
    primary = "merge_idem_primary"
    secondary = "merge_idem_secondary"
    _cleanup_contact(primary)
    _cleanup_contact(secondary)
    me.increment_message(primary, 1777467503000)
    me.increment_message(secondary, 1777467505000)

    with patch("src.services.contact_merge.Path.exists", return_value=False):
        with patch("src.services.contact_merge.shutil.rmtree", MagicMock()):
            merge_contacts(primary, secondary)
            result2 = merge_contacts(primary, secondary)

    assert isinstance(result2, dict)
