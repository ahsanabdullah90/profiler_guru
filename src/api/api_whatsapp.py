import base64
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.engine.metrics_engine import MetricsEngine
from src.services.name_matcher import find_similar_contacts
from src.storage.storage_manager import StorageManager
from src.utils.config import config
from src.utils.logger import logger

router = APIRouter(prefix="/api/v1/whatsapp", tags=["WhatsApp"])

_PHONE_RE = re.compile(r"@c\.us$")
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _normalize_phone(raw: str) -> str:
    """Extract numeric portion from a WhatsApp contact ID or phone string."""
    cleaned = _PHONE_RE.sub("", raw)
    return re.sub(r"\D", "", cleaned)


def _epoch_ms(ts_sec: int) -> int:
    return ts_sec * 1000


class WhatsAppIngestRequest(BaseModel):
    timestamp: int
    from_number: str = Field("", alias="from")
    fromMe: bool = False  # noqa: N815 — matches listener.js payload
    body: str = ""
    type: str = "chat"
    contact_name: str = "Unknown"
    phone: str = ""
    quoted_body: str | None = None
    quoted_author: str | None = None
    media_data: str | None = None
    media_mimetype: str | None = None

    model_config = {"populate_by_name": True}


def _get_or_create_chat_name(phone: str, contact_name: str, metrics_engine: MetricsEngine) -> tuple[str, bool]:
    """Try to find existing chat_name by phone; return (chat_name, did_merge).

    If no match by phone, return contact_name as-is.
    """
    normalized = _normalize_phone(phone)
    if len(normalized) >= 8:
        profile = metrics_engine.find_profile_by_whatsapp(normalized)
        if profile and profile.get("chat_name"):
            return profile["chat_name"], True  # merged with existing
    return contact_name, False  # new contact


@router.post("/ingest", status_code=200)
def ingest_whatsapp_message(data: WhatsAppIngestRequest):
    """Receive a live WhatsApp message from listener.js and store it."""
    try:
        metrics = MetricsEngine()
        sm = StorageManager(config.CHATS_DIR)

        ts_ms = _epoch_ms(data.timestamp)

        # Auto-merge by phone
        chat_name, merged = _get_or_create_chat_name(
            data.from_number or data.phone, data.contact_name, metrics
        )

        # Determine sender
        if data.fromMe:
            sender = "Me"
        else:
            sender = data.contact_name

        # Format quoted message as inline text
        text = data.body or ""
        if data.quoted_body and data.quoted_author:
            text = f"> [Reply] {data.quoted_author}: {data.quoted_body}\n{text}"

        media_type = None
        media_local_path = None

        # Handle audio
        if data.type in ("ptt", "audio") and data.media_data:
            audio_dir = Path(config.CHATS_DIR) / chat_name / "Audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_filename = f"{data.timestamp}.ogg"
            audio_path = audio_dir / audio_filename
            try:
                audio_bytes = base64.b64decode(data.media_data)
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                media_type = "audio"
                media_local_path = str(audio_path)
                text = "[Audio Transcription: Processing...]"
            except Exception as e:
                logger.error(f"Failed to decode audio for {chat_name}: {e}")

        # Save message
        content, file_path, month_id = sm.save_message(
            chat_name, sender, text, ts_ms, media_type, media_local_path
        )

        # Increment metrics
        metrics.increment_message(chat_name, ts_ms)
        metrics.record_platform(chat_name, "whatsapp", ts_ms)

        # If merged with existing IG contact, ensure instagram platform is recorded
        if merged:
            try:
                profile = metrics.get_client_profile(chat_name)
                if profile and profile.get("instagram_handle"):
                    metrics.record_platform(chat_name, "instagram", ts_ms)
            except Exception:
                pass

        # Enqueue audio transcription
        if media_type == "audio" and media_local_path:
            try:
                from src.engine.transcription_queue import transcription_queue
                transcription_queue.enqueue(chat_name, month_id, sender, datetime.fromtimestamp(data.timestamp).strftime("%Y-%m-%d %H:%M:%S"), media_local_path)
            except Exception as e:
                logger.error(f"Failed to enqueue transcription for {chat_name}: {e}")

        # Check for name-based merge suggestions (new contact only)
        suggestions = 0
        if not merged:
            try:
                all_names = list(metrics.get_all_contact_metadata_with_counts().keys())
                # Exclude the new contact from its own similarity check
                existing_names = [n for n in all_names if n != chat_name]
                similar = find_similar_contacts(data.contact_name, existing_names, threshold=0.72)
                for similar_name, score in similar:
                    metrics.create_pending_merge(
                        new_chat_name=chat_name,
                        existing_chat_name=similar_name,
                        reason=f"Name similarity ({score:.0%}) via WhatsApp import",
                        similarity=score,
                    )
                    suggestions += 1
            except Exception as e:
                logger.error(f"Name similarity check failed for {chat_name}: {e}")

        # Invalidate cache
        try:
            from src.utils.redis_client import invalidate_contacts_cache
            invalidate_contacts_cache()
        except Exception:
            pass

        return {
            "status": "ok",
            "merged_with": chat_name if merged else None,
            "merge_suggestions": suggestions,
            "audio": media_type == "audio",
        }

    except Exception as e:
        logger.error(f"WhatsApp ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/status")
def whatsapp_status():
    """Return WhatsApp bridge status."""
    try:
        metrics = MetricsEngine()
        all_platforms = metrics.get_all_platforms()
        wa_contacts = {cn for cn, plats in all_platforms.items() if "whatsapp" in plats}
        total_messages = 0
        last_seen = None
        for cn in wa_contacts:
            platforms = metrics.get_platforms(cn)
            for p in platforms:
                if p["platform"] == "whatsapp":
                    total_messages += p["message_count"]
                    if p["last_seen"] and (last_seen is None or p["last_seen"] > last_seen):
                        last_seen = p["last_seen"]

        pending = metrics.get_pending_merges_count()

        return {
            "bridge_online": True,
            "last_message_at": last_seen,
            "total_messages": total_messages,
            "contacts_count": len(wa_contacts),
            "pending_merges": pending,
        }
    except Exception as e:
        logger.error(f"WhatsApp status error: {e}")
        return {"bridge_online": False, "last_message_at": None, "total_messages": 0, "contacts_count": 0, "pending_merges": 0}


@router.post("/migrate")
def migrate_whatsapp_xml(xml_dir: str = ""):
    """Migrate existing WhatsApp XML exports to Profile-Guru markdown format.

    Re-runnable (idempotent) — skips messages already migrated via chunk_id dedup.
    """
    if not xml_dir:
        xml_dir = str(_PROJECT_ROOT / "Whatsapp-Bridge" / "Data" / "Chats")

    xml_path = Path(xml_dir)
    if not xml_path.exists():
        raise HTTPException(status_code=400, detail=f"XML directory not found: {xml_dir}")

    try:
        import xml.etree.ElementTree as ET_tree

        metrics = MetricsEngine()
        sm = StorageManager(config.CHATS_DIR)

        migrated = 0
        skipped = 0
        audio_enqueued = 0
        contacts_done = set()
        auto_merged = 0
        suggestions = 0

        # Scan for {contact}_{year}.xml files
        for xml_file in sorted(xml_path.glob("**/*.xml")):
            contact_name = xml_file.stem.rsplit("_", 1)[0] if "_" in xml_file.stem else xml_file.stem
            if xml_file.stat().st_size == 0:
                continue

            xml_tree = ET_tree.parse(xml_file)
            xml_root = xml_tree.getroot()

            for msg in xml_root.findall("message"):
                ts_el = msg.find("timestamp")
                body_el = msg.find("body")
                sender_el = msg.find("sender")
                phone_el = msg.find("phone")
                quoted = msg.find("quoted_msg")
                audio_file_el = msg.find("audio_file")

                if ts_el is None or ts_el.text is None:
                    continue

                ts = int(ts_el.text)
                ts_ms = _epoch_ms(ts)
                body_text = body_el.text or "" if body_el is not None else ""
                sender_text = sender_el.text or "" if sender_el is not None else ""
                phone_text = phone_el.text or "" if phone_el is not None else ""

                is_from_me = sender_text.lower() == "me"

                # Determine chat_name via auto-merge
                chat_name, merged = _get_or_create_chat_name(phone_text, contact_name, metrics)
                if merged:
                    auto_merged += 1

                # Format quoted
                text = body_text
                if quoted is not None:
                    q_author = quoted.find("author")
                    q_body = quoted.find("body")
                    author = q_author.text if q_author is not None and q_author.text else ""
                    q_text = q_body.text if q_body is not None and q_body.text else ""
                    text = f"> [Reply] {author}: {q_text}\n{body_text}"

                media_type = None
                media_local_path = None

                # Handle audio
                if audio_file_el is not None and audio_file_el.text:
                    audio_filename = audio_file_el.text
                    src_audio = xml_file.parent / "Audio" / audio_filename
                    if src_audio.exists():
                        audio_dir = Path(config.CHATS_DIR) / chat_name / "Audio"
                        audio_dir.mkdir(parents=True, exist_ok=True)
                        dst_audio = audio_dir / audio_filename
                        if not dst_audio.exists():
                            import shutil
                            shutil.copy2(str(src_audio), str(dst_audio))
                        media_type = "audio"
                        media_local_path = str(dst_audio)
                        text = "[Audio Transcription: Processing...]"

                # Determine sender
                sender_final = "Me" if is_from_me else sender_text

                try:
                    content, file_path, month_id = sm.save_message(
                        chat_name, sender_final, text, ts_ms, media_type, media_local_path
                    )
                    migrated += 1
                except Exception:
                    skipped += 1
                    continue

                metrics.increment_message(chat_name, ts_ms)
                metrics.record_platform(chat_name, "whatsapp", ts_ms)

                if merged:
                    try:
                        profile = metrics.get_client_profile(chat_name)
                        if profile and profile.get("instagram_handle"):
                            metrics.record_platform(chat_name, "instagram", ts_ms)
                    except Exception:
                        pass

                if media_type == "audio" and media_local_path:
                    try:
                        from src.engine.transcription_queue import transcription_queue
                        transcription_queue.enqueue(
                            chat_name, month_id, sender_final,
                            datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                            media_local_path,
                        )
                        audio_enqueued += 1
                    except Exception as e:
                        logger.error(f"Failed to enqueue transcription: {e}")

                contacts_done.add(chat_name)

            # Name similarity suggestions for each new contact in this XML file
            if contact_name not in {c for c in contacts_done if c == contact_name}:
                try:
                    existing_names = list(metrics.get_all_contact_metadata_with_counts().keys())
                    similar = find_similar_contacts(contact_name, existing_names, threshold=0.72)
                    for similar_name, score in similar:
                        metrics.create_pending_merge(
                            new_chat_name=contact_name,
                            existing_chat_name=similar_name,
                            reason=f"Name similarity ({score:.0%}) via WhatsApp XML migration",
                            similarity=score,
                        )
                        suggestions += 1
                except Exception:
                    pass

        try:
            from src.utils.redis_client import invalidate_contacts_cache
            invalidate_contacts_cache()
        except Exception:
            pass

        return {
            "migrated": migrated,
            "skipped_duplicates": skipped,
            "audio_enqueued": audio_enqueued,
            "contacts": len(contacts_done),
            "auto_merged": auto_merged,
            "merge_suggestions": suggestions,
        }

    except Exception as e:
        logger.error(f"WhatsApp XML migration error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
