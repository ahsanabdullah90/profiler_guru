import os
import shutil
from datetime import datetime
from pathlib import Path

from src.engine.metrics_engine import MetricsEngine
from src.engine.rag_engine import rag_engine
from src.storage.storage_manager import StorageManager
from src.utils.config import config
from src.utils.logger import logger


def cleanup_quarterly_logs():
    """Migrate legacy quarterly markdown logs to monthly logs and delete them.

    Steps:
    1. Scan the contacts directory for files matching the pattern "*_Q*.md" inside the Chats subdirectory.
    2. For each block in a quarterly file, extract the timestamp (from the header).
    3. Determine the target month string "YYYY_MM" and ensure a monthly file exists.
    4. Use the existing signature cache to avoid duplicate messages.
    5. Append the block to the appropriate monthly markdown via StorageManager.save_message.
    6. Update MetricsEngine and RAG index for newly added messages.
    7. Delete the quarterly file's old chunks from ChromaDB.
    8. After processing, move the original quarterly file to a "deprecated" folder.
    9. Run the global self-healing deduplication process to completely rebuild database metrics and the RAG index from clean monthly logs.
    """
    chats_dir = Path(config.CHATS_DIR)
    if not chats_dir.exists():
        logger.warning(f"Chats directory {chats_dir} does not exist; nothing to clean.")
        return

    storage_manager = StorageManager(chats_dir)
    metrics_engine = MetricsEngine()

    deprecated_dir = chats_dir / "deprecated_quarterly"
    deprecated_dir.mkdir(parents=True, exist_ok=True)

    modified_any = False

    for contact in os.listdir(chats_dir):
        contact_path = chats_dir / contact
        if not contact_path.is_dir() or contact == "deprecated_quarterly":
            continue

        contact_chats_dir = contact_path / "Chats"
        if not contact_chats_dir.exists():
            continue

        # List quarterly markdown files
        quarterly_files = [f for f in os.listdir(contact_chats_dir) if f.endswith('.md') and ('_Q' in f or '_q' in f)]
        if not quarterly_files:
            continue

        logger.info(f"Processing legacy quarterly files for contact '{contact}': {quarterly_files}")
        modified_any = True

        # Load existing signatures for this contact to avoid duplicates
        signatures = set()
        # Load signatures from all existing monthly files first
        monthly_files = [f for f in os.listdir(contact_chats_dir) if f.endswith('.md') and not ('_Q' in f or '_q' in f)]
        for m_file in monthly_files:
            file_path = contact_chats_dir / m_file
            try:
                with open(file_path, encoding='utf-8') as f:
                    content = f.read()
                for block in content.split('---'):
                    block = block.strip()
                    if not block:
                        continue
                    lines = block.split('\n')
                    header = lines[0].strip()
                    if header.startswith('### ['):
                        closing = header.find(']')
                        if closing != -1:
                            time_str = header[5:closing]
                            sender = header[closing + 2:].strip()
                            signatures.add((sender, time_str))
            except Exception as e:
                logger.error(f"Failed to load signatures from {file_path}: {e}")

        # Process each quarterly file
        for q_file in quarterly_files:
            q_path = contact_chats_dir / q_file
            q_month = q_file[:-3]  # e.g., "2026_Q2"
            try:
                with open(q_path, encoding='utf-8') as f:
                    q_content = f.read()
                for block in q_content.split('---'):
                    block = block.strip()
                    if not block:
                        continue
                    lines = block.split('\n')
                    header = lines[0].strip()
                    if not header.startswith('### ['):
                        continue
                    closing = header.find(']')
                    if closing == -1:
                        continue
                    time_str = header[5:closing]
                    sender = header[closing + 2:].strip()
                    # Skip if already present
                    if (sender, time_str) in signatures:
                        continue
                    # Parse timestamp to month identifier
                    try:
                        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                        month_id = f"{dt.year}_{dt.month:02d}"  # e.g., 2026_06
                    except Exception:
                        logger.warning(f"Unable to parse timestamp '{time_str}' in {q_path}; skipping block.")
                        continue
                    # Determine message content (everything after header)
                    text = '\n'.join(lines[1:]).strip()
                    # Save message using storage manager (media_type=None, media_path=None)
                    content, _, _ = storage_manager.save_message(contact, sender, text, int(dt.timestamp() * 1000), None, None)
                    # Update signatures to prevent future duplicates
                    signatures.add((sender, time_str))
                    # Update metrics and RAG index
                    metrics_engine.increment_message(contact, int(dt.timestamp() * 1000))
                    rag_engine.add_messages_batch([(contact, month_id, content)])

                # Delete legacy quarterly chunks from ChromaDB
                try:
                    with rag_engine._lock:
                        rag_engine.collection.delete(where={"$and": [{"chat_name": contact}, {"month": q_month}]})
                    logger.info(f"Deleted legacy quarterly RAG chunks for {contact} ({q_month}) from ChromaDB.")
                except Exception as e:
                    logger.error(f"Failed to delete quarterly RAG chunks for {contact} ({q_month}): {e}")

                # Move processed quarterly file to deprecated folder
                dest_path = deprecated_dir / f"{contact}_{q_file}"
                shutil.move(str(q_path), str(dest_path))
                logger.info(f"Moved legacy quarterly file {q_path} to {dest_path}")
            except Exception as e:
                logger.error(f"Failed to process quarterly file {q_path}: {e}")

    if modified_any:
        logger.info("Running global self-healing data deduplication to repair metrics and RAG indices...")
        from src.engine.self_healing import deduplicate_all_data
        deduplicate_all_data()

    logger.info("Legacy quarterly cleanup completed.")

if __name__ == "__main__":
    cleanup_quarterly_logs()
