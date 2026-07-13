"""
PROJECT: Profile Guru
COMPONENT: scripts/repair_contact_names.py

This script repairs contact names that fail validation due to emojis, carets, 
or other special characters. It renames the corresponding filesystem folders 
and updates SQLite records. If a sanitized contact name already exists in the 
database, the script safely merges both contacts using the existing merge service.
"""

import os
import sys
import sqlite3
import shutil
import re
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.config import config
from src.utils.logger import logger
from src.utils.sanitize import sanitize_contact_name
from src.engine.metrics_engine import MetricsEngine
from src.services.contact_merge import merge_contacts

CONTACT_NAME_REGEX = re.compile(r"^[\w\-\. ]{1,100}$", re.UNICODE)


def is_valid_name(name: str) -> bool:
    return bool(name and CONTACT_NAME_REGEX.match(name))


def repair_all_contacts():
    logger.info("Initializing repair process for invalid contact names...")

    metrics = MetricsEngine()
    db_path = metrics.db_path
    chats_dir = Path(config.CHATS_DIR)

    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return

    # 1. Identify all invalid contact names from both database and filesystem
    invalid_names = set()

    # Scan database tables
    conn = sqlite3.connect(str(db_path))
    try:
        # Get tables
        tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        
        # Look for columns that might hold contact names
        for table in tables:
            columns = [col[1] for col in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            name_cols = [c for c in columns if c in ("chat_name", "contact_name")]
            for col in name_cols:
                rows = conn.execute(f"SELECT DISTINCT [{col}] FROM [{table}] WHERE [{col}] IS NOT NULL").fetchall()
                for r in rows:
                    name = r[0]
                    if not is_valid_name(name):
                        invalid_names.add(name)
    finally:
        conn.close()

    # Scan disk chats directory
    if chats_dir.exists():
        for d in chats_dir.iterdir():
            if d.is_dir() and not is_valid_name(d.name):
                invalid_names.add(d.name)

    if not invalid_names:
        logger.info("No invalid contact names found. Everything is clean!")
        return

    logger.info(f"Found {len(invalid_names)} invalid contact names to process.")

    # Process each invalid name
    for old_name in sorted(invalid_names):
        new_name = sanitize_contact_name(old_name)
        if old_name == new_name:
            continue

        logger.info(f"Repairing: '{old_name}' -> '{new_name}'")

        # Check if the sanitized name already exists in the database
        conn = sqlite3.connect(str(db_path))
        exists_in_db = False
        try:
            profile_exists = conn.execute(
                "SELECT COUNT(*) FROM client_profiles WHERE chat_name = ?", (new_name,)
            ).fetchone()[0] > 0
            metadata_exists = conn.execute(
                "SELECT COUNT(*) FROM contact_metadata WHERE chat_name = ?", (new_name,)
            ).fetchone()[0] > 0
            exists_in_db = profile_exists or metadata_exists
        finally:
            conn.close()

        # Check filesystem existence
        old_folder = chats_dir / old_name
        new_folder = chats_dir / new_name

        if exists_in_db or new_folder.exists():
            # COLLISION CASE: Must merge contacts to preserve all history
            logger.info(f"Collision detected for '{new_name}'. Merging '{old_name}' into '{new_name}'...")
            
            # If the database doesn't have the target record, make sure it has one so merge_contacts succeeds
            conn = sqlite3.connect(str(db_path))
            try:
                target_exists = conn.execute("SELECT COUNT(*) FROM contact_metadata WHERE chat_name = ?", (new_name,)).fetchone()[0] > 0
                if not target_exists:
                    # Create placeholder target metadata so the merge service doesn't fail
                    with conn:
                        conn.execute(
                            "INSERT OR IGNORE INTO contact_metadata (chat_name, message_count, last_snippet, last_date) VALUES (?, 0, '', '')",
                            (new_name,)
                        )
                        conn.execute(
                            "INSERT OR IGNORE INTO client_profiles (chat_name, client_id, canonical_name) VALUES (?, ?, ?)",
                            (new_name, metrics.get_or_create_client_id(new_name), new_name)
                        )
            finally:
                conn.close()

            # Execute merge
            try:
                res = merge_contacts(primary_chat_name=new_name, secondary_chat_name=old_name)
                logger.info(f"Successfully merged '{old_name}' into '{new_name}'. Result: {res}")
            except Exception as merge_err:
                logger.error(f"Failed to merge '{old_name}' into '{new_name}': {merge_err}")
        else:
            # SIMPLE RENAME CASE: Update SQLite tables and rename folder
            logger.info(f"Simple rename case. Updating database and filesystem...")

            # 1. Rename folder on disk
            if old_folder.exists():
                try:
                    shutil.move(str(old_folder), str(new_folder))
                    logger.info(f"Renamed folder on disk to {new_folder.name}")
                except Exception as disk_err:
                    logger.error(f"Failed to rename folder on disk: {disk_err}")
                    continue

            # 2. Update SQLite database tables
            conn = sqlite3.connect(str(db_path))
            try:
                tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                with conn:
                    for table in tables:
                        # Find columns in this table
                        columns = [col[1] for col in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                        
                        # Update columns matching chat_name or contact_name
                        for col in columns:
                            if col in ("chat_name", "contact_name"):
                                cur = conn.execute(
                                    f"UPDATE [{table}] SET [{col}] = ? WHERE [{col}] = ?",
                                    (new_name, old_name)
                                )
                                if cur.rowcount > 0:
                                    logger.info(f"Updated {cur.rowcount} rows in table '{table}', column '{col}'")
            except Exception as db_err:
                logger.error(f"Failed to update database for '{old_name}': {db_err}")
            finally:
                conn.close()

    logger.info("Repair process complete.")


if __name__ == "__main__":
    repair_all_contacts()
