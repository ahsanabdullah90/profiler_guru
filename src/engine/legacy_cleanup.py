import os
import json
import shutil
from pathlib import Path
from datetime import datetime

from src.utils.config import config
from src.utils.logger import logger
from src.storage.storage_manager import StorageManager
from src.engine.metrics_engine import MetricsEngine
from src.engine.rag_engine import rag_engine


def cleanup_quarterly_logs():
    """Migrate legacy quarterly markdown logs to monthly logs and delete them.

    Steps:
    1. Scan the contacts directory for files matching the pattern "*_Q*.md".
    2. For each block in a quarterly file, extract the timestamp (from the header).
    3. Determine the target month string "YYYY_MM" and ensure a monthly file exists.
    4. Use the existing signature cache to avoid duplicate messages.
    5. Append the block to the appropriate monthly markdown via StorageManager.save_message.
    6. Update MetricsEngine and RAG index for newly added messages.
    7. After processing, move the original quarterly file to a "deprecated" folder.
    """
    chats_dir = Path(config.CHATS_DIR)
    if not chats_dir.exists():
        logger.warning(f"Chats directory {chats_dir} does not exist; nothing to clean.")
        return

    storage_manager = StorageManager(chats_dir)
    metrics_engine = MetricsEngine()

    deprecated_dir = chats_dir / "deprecated_quarterly"
    deprecated_dir.mkdir(parents=True, exist_ok=True)

    for contact in os.listdir(chats_dir):
        contact_path = chats_dir / contact
        if not contact_path.is_dir():
            continue
        # List quarterly markdown files
        quarterly_files = [f for f in os.listdir(contact_path) if f.endswith('.md') and ('_Q' in f or '_q' in f)]
        if not quarterly_files:
            continue
        logger.info(f"Processing legacy quarterly files for contact '{contact}': {quarterly_files}")
        # Load existing signatures for this contact to avoid duplicates
        signatures = set()
        # Load signatures from all existing monthly files first
        monthly_files = [f for f in os.listdir(contact_path) if f.endswith('.md') and not ('_Q' in f or '_q' in f)]
        for m_file in monthly_files:
            file_path = contact_path / m_file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
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
            q_path = contact_path / q_file
            try:
                with open(q_path, 'r', encoding='utf-8') as f:
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
                # Move processed quarterly file to deprecated folder
                dest_path = deprecated_dir / f"{contact}_{q_file}"
                shutil.move(str(q_path), str(dest_path))
                logger.info(f"Moved legacy quarterly file {q_path} to {dest_path}")
            except Exception as e:
                logger.error(f"Failed to process quarterly file {q_path}: {e}")

    logger.info("Legacy quarterly cleanup completed.")

if __name__ == "__main__":
    cleanup_quarterly_logs()
