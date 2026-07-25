import re
import shutil
from pathlib import Path

from src.engine.metrics_engine import MetricsEngine
from src.storage.storage_manager import StorageManager
from src.utils.config import config
from src.utils.logger import logger
from src.utils.markdown import parse_message_blocks


def merge_contacts(primary_chat_name: str, secondary_chat_name: str) -> dict:
    """Merge all data from secondary contact into primary, then delete secondary.

    Returns a summary dict with counts of merged records.
    """
    if primary_chat_name == secondary_chat_name:
        return {"error": "Cannot merge a contact with itself"}

    metrics = MetricsEngine()
    
    # Warn if manual client is being used as secondary — this would discard its display_name
    primary_profile = metrics.get_client_profile(primary_chat_name)
    if primary_profile and primary_profile.get("source") == "manual":
        # manual client as primary is the canonical and safe direction
        pass
    secondary_profile = metrics.get_client_profile(secondary_chat_name)
    if secondary_profile and secondary_profile.get("source") == "manual":
        logger.warning(
            f"Merge: manual client '{secondary_chat_name}' used as secondary. "
            "display_name and profile fields from the manual record may be demoted."
        )

    sm = StorageManager(config.CHATS_DIR)

    summary = {
        "markdown_messages": 0,
        "audio_files": 0,
        "notes": 0,
        "consents": 0,
        "assessments": 0,
        "session_audio": 0,
        "deleted_vectors": 0,
    }

    # ---- 1. Merge markdown files (append secondary -> primary, dedup by chunk_id) ----
    _merge_markdown_files(primary_chat_name, secondary_chat_name, sm, summary)

    # ---- 2. Merge audio files ----
    _merge_audio_files(primary_chat_name, secondary_chat_name, summary)

    # ---- 3. Delete secondary chats directory ----
    secondary_chat_dir = Path(config.CHATS_DIR) / secondary_chat_name
    if secondary_chat_dir.exists():
        shutil.rmtree(secondary_chat_dir)

    # ---- 4. Merge SQLite records ----
    primary_profile = metrics.get_client_profile(primary_chat_name)
    secondary_profile = metrics.get_client_profile(secondary_chat_name)

    with metrics._write_lock:
        cur = metrics.conn.cursor()

        # 4a. Merge contact_metadata
        _merge_contact_metadata(cur, primary_chat_name, secondary_chat_name, metrics)

        # 4b. Merge connection_metrics
        _merge_connection_metrics(cur, primary_chat_name, secondary_chat_name)

        # 4c. Merge contact_platforms
        _merge_contact_platforms(cur, primary_chat_name, secondary_chat_name)

        # 4d. Merge client_profiles (copy empty fields from secondary)
        _merge_client_profiles(cur, primary_chat_name, secondary_chat_name, primary_profile, secondary_profile, summary)

        # 4e. Reassign clinical notes
        _reassign_notes(cur, primary_chat_name, secondary_chat_name, primary_profile, summary)

        # 4f. Reassign consents
        _reassign_consents(cur, primary_chat_name, secondary_chat_name, primary_profile, summary)

        # 4g. Reassign assessments
        _reassign_assessments(cur, primary_chat_name, secondary_chat_name, primary_profile, summary)

        # 4h. Reassign session audio
        _reassign_session_audio(cur, primary_chat_name, secondary_chat_name, primary_profile, summary)

        # 4i. Delete secondary contact_metadata
        cur.execute("DELETE FROM contact_metadata WHERE chat_name = ?;", (secondary_chat_name,))

        metrics.conn.commit()

    # ---- 5. Re-index RAG for primary, delete secondary vectors ----
    try:
        from src.engine.rag_engine import rag_engine as _rag
        _rag.delete_vectors_by_contact(secondary_chat_name)
        summary["deleted_vectors"] = 1

        # Re-index primary using merged markdown files
        primary_dir = Path(config.CHATS_DIR) / primary_chat_name / "Chats"
        if primary_dir.exists():
            batch_data = []
            for fname in sorted(primary_dir.iterdir()):
                if fname.suffix == ".md":
                    text = fname.read_text(encoding="utf-8")
                    month = fname.stem
                    batch_data.append((primary_chat_name, month, text))
            if batch_data:
                _rag.add_messages_batch(batch_data)
    except Exception as e:
        logger.error(f"RAG re-index failed during merge: {e}")

    # ---- 6. Mark pending merges as merged ----
    metrics.mark_pending_merge_merged(primary_chat_name)
    metrics.mark_pending_merge_merged(secondary_chat_name)

    # ---- 7. Invalidate cache ----
    try:
        from src.utils.redis_client import invalidate_contacts_cache
        invalidate_contacts_cache()
    except Exception:
        pass

    return summary


def _merge_markdown_files(
    primary: str, secondary: str,
    sm: StorageManager, summary: dict,
):
    """Append secondary's markdown messages to primary's monthly files, dedup by chunk_id."""
    secondary_chats_dir = Path(config.CHATS_DIR) / secondary / "Chats"
    primary_chats_dir = Path(config.CHATS_DIR) / primary / "Chats"

    if not secondary_chats_dir.exists():
        return

    primary_chats_dir.mkdir(parents=True, exist_ok=True)

    # Build primary's existing chunk_ids for dedup
    primary_chunk_ids: set[str] = set()
    if primary_chats_dir.exists():
        for fname in primary_chats_dir.iterdir():
            if fname.suffix == ".md":
                text = fname.read_text(encoding="utf-8")
                for match in re.findall(r"<!--\s*chunk_id:\s*([a-f0-9]+)\s*-->", text):
                    primary_chunk_ids.add(match)

    for fname in sorted(secondary_chats_dir.iterdir()):
        if fname.suffix != ".md":
            continue
        text = fname.read_text(encoding="utf-8")
        blocks = parse_message_blocks(text)
        if not blocks:
            continue

        new_blocks = []
        for block in blocks:
            chunk_id_match = re.search(r"<!--\s*chunk_id:\s*([a-f0-9]+)\s*-->", block)
            if chunk_id_match and chunk_id_match.group(1) in primary_chunk_ids:
                continue  # Skip duplicate
            new_blocks.append(block.strip())

        if not new_blocks:
            continue

        target_path = primary_chats_dir / fname.name
        existing = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        if existing and not existing.endswith("\n---\n"):
            existing = existing.rstrip() + "\n---\n"
        appended = "\n---\n".join(new_blocks) + "\n"
        if existing:
            appended = existing + "\n---\n" + appended

        target_path.write_text(appended, encoding="utf-8")
        summary["markdown_messages"] += len(new_blocks)


def _merge_audio_files(primary: str, secondary: str, summary: dict):
    """Move secondary contact's audio files to primary's audio directory."""
    secondary_audio = Path(config.CHATS_DIR) / secondary / "Audio"
    primary_audio = Path(config.CHATS_DIR) / primary / "Audio"

    if not secondary_audio.exists():
        return

    primary_audio.mkdir(parents=True, exist_ok=True)

    for fname in secondary_audio.iterdir():
        if fname.is_file():
            dest = primary_audio / fname.name
            if not dest.exists():
                shutil.copy2(str(fname), str(dest))
                summary["audio_files"] += 1


def _merge_contact_metadata(cur, primary: str, secondary: str, metrics: MetricsEngine):
    """Sum message counts from secondary into primary."""
    primary_meta = metrics.get_contact_metadata(primary) or {"message_count": 0, "last_snippet": "", "last_date": ""}
    secondary_meta = metrics.get_contact_metadata(secondary) or {"message_count": 0, "last_snippet": "", "last_date": ""}

    new_count = (primary_meta.get("message_count") or 0) + (secondary_meta.get("message_count") or 0)
    # Keep the latest snippet and date
    last_date = primary_meta.get("last_date") or secondary_meta.get("last_date")
    if secondary_meta.get("last_date") and (not primary_meta.get("last_date") or secondary_meta["last_date"] > primary_meta["last_date"]):
        last_date = secondary_meta["last_date"]

    last_snippet = primary_meta.get("last_snippet") or secondary_meta.get("last_snippet")

    cur.execute(
        "INSERT INTO contact_metadata (chat_name, message_count, last_snippet, last_date) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(chat_name) DO UPDATE SET "
        "  message_count = excluded.message_count,"
        "  last_snippet = excluded.last_snippet,"
        "  last_date = excluded.last_date;",
        (primary, new_count, last_snippet, last_date),
    )


def _merge_connection_metrics(cur, primary: str, secondary: str):
    """Sum daily connection_metrics from secondary into primary."""
    cur.execute(
        "INSERT INTO connection_metrics (chat_name, date, message_count) "
        "SELECT ?, date, message_count FROM connection_metrics WHERE chat_name = ? "
        "ON CONFLICT(chat_name, date) DO UPDATE SET "
        "  message_count = message_count + excluded.message_count;",
        (primary, secondary),
    )
    cur.execute("DELETE FROM connection_metrics WHERE chat_name = ?;", (secondary,))


def _merge_contact_platforms(cur, primary: str, secondary: str):
    """Merge platform rows from secondary into primary."""
    cur.execute(
        "INSERT INTO contact_platforms (chat_name, platform, first_seen, last_seen, message_count) "
        "SELECT ?, platform, first_seen, last_seen, message_count FROM contact_platforms WHERE chat_name = ? "
        "ON CONFLICT(chat_name, platform) DO UPDATE SET "
        "  message_count = message_count + excluded.message_count,"
        "  last_seen = MAX(last_seen, excluded.last_seen),"
        "  first_seen = MIN(first_seen, excluded.first_seen);",
        (primary, secondary),
    )
    cur.execute("DELETE FROM contact_platforms WHERE chat_name = ?;", (secondary,))


def _merge_client_profiles(cur, primary: str, secondary: str, primary_profile: dict | None, secondary_profile: dict | None, summary: dict):
    """Copy empty fields from secondary's profile into primary's profile."""
    if not primary_profile and not secondary_profile:
        return

    fields = ["display_name", "email", "mobile", "whatsapp", "instagram_handle", "dob", "national_id"]
    updates = {}
    for f in fields:
        primary_val = primary_profile.get(f) if primary_profile else None
        secondary_val = secondary_profile.get(f) if secondary_profile else None
        if not primary_val and secondary_val:
            if f == "national_id":
                from src.engine.encryption import encrypt
                updates[f] = encrypt(secondary_val)
            else:
                updates[f] = secondary_val
            summary[f"copied_{f}"] = 1

    if updates:
        set_parts = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values())
        cur.execute(
            f"UPDATE client_profiles SET {set_parts} WHERE chat_name = ?;",
            (*values, primary),
        )

    # Delete secondary profile
    cur.execute("DELETE FROM client_profiles WHERE chat_name = ?;", (secondary,))


def _reassign_notes(cur, primary: str, secondary: str, primary_profile: dict | None, summary: dict):
    """Reassign clinical notes from secondary contact to primary."""
    primary_patient_id = primary_profile.get("patient_id") if primary_profile else None
    if primary_patient_id:
        cur.execute(
            "UPDATE clinical_notes SET contact_name = ?, patient_id = ? WHERE contact_name = ?;",
            (primary, primary_patient_id, secondary),
        )
        summary["notes"] = cur.rowcount


def _reassign_consents(cur, primary: str, secondary: str, primary_profile: dict | None, summary: dict):
    """Reassign patient consents from secondary patient_id to primary's."""
    primary_patient_id = primary_profile.get("patient_id") if primary_profile else None
    if primary_patient_id:
        cur.execute(
            "UPDATE patient_consents SET patient_id = ? WHERE patient_id = (SELECT patient_id FROM client_profiles WHERE chat_name = ?);",
            (primary_patient_id, secondary),
        )
        summary["consents"] = cur.rowcount


def _reassign_assessments(cur, primary: str, secondary: str, primary_profile: dict | None, summary: dict):
    """Reassign assessment history from secondary to primary."""
    primary_patient_id = primary_profile.get("patient_id") if primary_profile else None
    if primary_patient_id:
        cur.execute(
            "UPDATE assessment_history SET contact_name = ?, patient_id = ? WHERE contact_name = ?;",
            (primary, primary_patient_id, secondary),
        )
        summary["assessments"] = cur.rowcount


def _reassign_session_audio(cur, primary: str, secondary: str, primary_profile: dict | None, summary: dict):
    """Reassign session audio records from secondary to primary."""
    primary_patient_id = primary_profile.get("patient_id") if primary_profile else None
    if primary_patient_id:
        cur.execute(
            "UPDATE session_audio SET patient_id = ? WHERE patient_id = (SELECT patient_id FROM client_profiles WHERE chat_name = ?);",
            (primary_patient_id, secondary),
        )
        summary["session_audio"] = cur.rowcount
