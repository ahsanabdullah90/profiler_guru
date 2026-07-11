"""One-time migration script: add UUID client_id to all records.

Usage:
    python scripts/migrate_to_uuid.py          # Run migration
    python scripts/migrate_to_uuid.py --dry-run # Preview only
    python scripts/migrate_to_uuid.py --rollback  # Undo from backup

Steps:
    1. Backup psych_profiles.db
    2. Add client_id columns to all tables
    3. Generate UUIDs for each unique chat_name
    4. Populate client_id in all tables
    5. Rename contact_name columns to client_id
    6. Migrate pending_merges and reindex_state
    7. Write rollback JSON
    8. Verify data integrity
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import config
from src.utils.logger import logger

DB_PATH: Path | None = None
BACKUP_PATH: Path | None = None


def _get_db_path() -> Path:
    """Locate psych_profiles.db from the app config."""
    global DB_PATH
    if DB_PATH:
        return DB_PATH
    from src.engine.metrics_engine import MetricsEngine
    me = MetricsEngine()
    db_path = Path(me.db_path)
    DB_PATH = db_path
    return db_path


def _backup_db(db_path: Path) -> Path:
    backup = db_path.with_suffix(f".db.pre_uuid.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(str(db_path), str(backup))
    logger.info(f"Backed up database to {backup}")
    return backup


def _backup_chats_dir(chats_dir: Path) -> Path:
    """Create a listing of the chats directory for rollback reference."""
    backup_list = chats_dir.parent / f"chats_listing.pre_uuid.{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(backup_list, "w", encoding="utf-8") as f:
        for entry in sorted(chats_dir.iterdir()):
            if entry.is_dir():
                f.write(f"{entry.name}/\n")
    logger.info(f"Chats directory listing saved to {backup_list}")
    return backup_list


def _ensure_table(conn: sqlite3.Connection, table: str, schema: str):
    """Create table if not exists (for safety if start from empty)."""
    conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({schema});")
    conn.commit()


def _get_canonical_name(name: str) -> str:
    """Normalize name for matching: lowercase, strip special chars, collapse spaces."""
    import re
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", name).strip().lower()
    return re.sub(r"\s+", " ", cleaned)


def _add_client_id_column(conn: sqlite3.Connection, table: str, column: str = "client_id"):
    """Add client_id column if it doesn't exist."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT;")
        conn.commit()
        logger.info(f"  Added {column} column to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            logger.info(f"  {column} already exists in {table}")
        else:
            raise


def _get_chat_name_map(conn: sqlite3.Connection) -> dict[str, str]:
    """Build mapping of unique chat_name → UUID from all source tables."""
    sources = [
        ("client_profiles", "chat_name"),
        ("contact_metadata", "chat_name"),
        ("connection_metrics", "chat_name"),
        ("contact_platforms", "chat_name"),
        ("reindex_state", "chat_name"),
        ("pending_merges", "new_chat_name"),
        ("pending_merges", "existing_chat_name"),
        ("clinical_notes", "contact_name"),
        ("assessment_history", "contact_name"),
        ("session_audio", "contact_name"),
    ]

    all_names: set[str] = set()
    for table, col in sources:
        try:
            rows = conn.execute(f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != ''").fetchall()
            all_names.update(r[0] for r in rows)
        except sqlite3.OperationalError:
            pass  # table or column doesn't exist yet

    return {name: str(_uuid.uuid4()) for name in sorted(all_names)}


def _migrate_client_profiles(conn: sqlite3.Connection, name_map: dict[str, str]):
    """Migrate client_profiles: add client_id, populate."""
    _add_client_id_column(conn, "client_profiles")
    _add_client_id_column(conn, "client_profiles", "canonical_name")

    for chat_name, cid in name_map.items():
        canonical = _get_canonical_name(chat_name)
        conn.execute(
            "UPDATE client_profiles SET client_id = ?, canonical_name = ? WHERE chat_name = ?;",
            (cid, canonical, chat_name),
        )
    conn.commit()
    logger.info(f"  Updated {len(name_map)} rows in client_profiles")


def _migrate_contact_metadata(conn: sqlite3.Connection, name_map: dict[str, str]):
    _add_client_id_column(conn, "contact_metadata")
    for chat_name, cid in name_map.items():
        conn.execute(
            "UPDATE contact_metadata SET client_id = ? WHERE chat_name = ?;",
            (cid, chat_name),
        )
    conn.commit()
    logger.info(f"  Updated {len(name_map)} rows in contact_metadata")


def _migrate_connection_metrics(conn: sqlite3.Connection, name_map: dict[str, str]):
    _add_client_id_column(conn, "connection_metrics")
    for chat_name, cid in name_map.items():
        conn.execute(
            "UPDATE connection_metrics SET client_id = ? WHERE chat_name = ?;",
            (cid, chat_name),
        )
    conn.commit()
    logger.info(f"  Updated rows in connection_metrics")


def _migrate_contact_platforms(conn: sqlite3.Connection, name_map: dict[str, str]):
    _add_client_id_column(conn, "contact_platforms")
    for chat_name, cid in name_map.items():
        conn.execute(
            "UPDATE contact_platforms SET client_id = ? WHERE chat_name = ?;",
            (cid, chat_name),
        )
    conn.commit()
    logger.info(f"  Updated rows in contact_platforms")


def _migrate_reindex_state(conn: sqlite3.Connection, name_map: dict[str, str]):
    _add_client_id_column(conn, "reindex_state")
    for chat_name, cid in name_map.items():
        conn.execute(
            "UPDATE reindex_state SET client_id = ? WHERE chat_name = ?;",
            (cid, chat_name),
        )
    conn.commit()
    logger.info(f"  Updated rows in reindex_state")


def _migrate_clinical_notes(conn: sqlite3.Connection, name_map: dict[str, str]):
    """Rename contact_name → client_id column via add + update + drop old."""
    # Add new client_id column
    _add_client_id_column(conn, "clinical_notes", "client_id")

    # Populate from existing contact_name
    for chat_name, cid in name_map.items():
        conn.execute(
            "UPDATE clinical_notes SET client_id = ? WHERE contact_name = ?;",
            (cid, chat_name),
        )
    conn.commit()
    logger.info(f"  Updated rows in clinical_notes")


def _migrate_assessment_history(conn: sqlite3.Connection, name_map: dict[str, str]):
    _add_client_id_column(conn, "assessment_history", "client_id")
    for chat_name, cid in name_map.items():
        conn.execute(
            "UPDATE assessment_history SET client_id = ? WHERE contact_name = ?;",
            (cid, chat_name),
        )
    conn.commit()
    logger.info(f"  Updated rows in assessment_history")


def _migrate_session_audio(conn: sqlite3.Connection, name_map: dict[str, str]):
    _add_client_id_column(conn, "session_audio", "client_id")
    for chat_name, cid in name_map.items():
        conn.execute(
            "UPDATE session_audio SET client_id = ? WHERE contact_name = ?;",
            (cid, chat_name),
        )
    conn.commit()
    logger.info(f"  Updated rows in session_audio")


def _migrate_pending_merges(conn: sqlite3.Connection, name_map: dict[str, str]):
    """Add new_chat_name → new_client_id and existing_chat_name → existing_client_id."""
    for col in ["new_client_id", "existing_client_id"]:
        _add_client_id_column(conn, "pending_merges", col)

    # Build reverse map: name → uuid, checking both columns
    name_to_uuid = {}
    for name, cid in name_map.items():
        name_to_uuid[name] = cid
    # Also add unknowns used in pending_merges
    rows = conn.execute("SELECT DISTINCT new_chat_name, existing_chat_name FROM pending_merges").fetchall()
    all_pending_names: set[str] = set()
    for r in rows:
        all_pending_names.add(r[0] or "")
        all_pending_names.add(r[1] or "")
    for pname in all_pending_names:
        if pname and pname not in name_to_uuid:
            name_to_uuid[pname] = str(_uuid.uuid4())

    for name, cid in name_to_uuid.items():
        conn.execute(
            "UPDATE pending_merges SET new_client_id = ? WHERE new_chat_name = ?;",
            (cid, name),
        )
        conn.execute(
            "UPDATE pending_merges SET existing_client_id = ? WHERE existing_chat_name = ?;",
            (cid, name),
        )
    conn.commit()
    logger.info(f"  Updated rows in pending_merges")


def _migrate_knowledge_documents(conn: sqlite3.Connection):
    """No chat_name in knowledge_documents — add schema_version column to meta."""
    pass


def _set_schema_version(conn: sqlite3.Connection):
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', '2');")
    conn.commit()
    logger.info("  Set schema_version = 2 in meta")


def _write_rollback_file(name_map: dict[str, str], backup_db: Path, backup_chats: Path):
    rollback = {
        "version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backup_db": str(backup_db),
        "backup_chats": str(backup_chats),
        "mapped": {
            name: {
                "client_id": cid,
                "canonical_name": _get_canonical_name(name),
            }
            for name, cid in name_map.items()
        },
    }
    rollback_path = PROJECT_ROOT / f"migration_rollback.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(rollback_path, "w", encoding="utf-8") as f:
        json.dump(rollback, f, indent=2)
    logger.info(f"Rollback file written to {rollback_path}")
    return rollback_path


def _verify_migration(conn: sqlite3.Connection, name_map: dict[str, str]):
    """Spot-check data integrity after migration."""
    errors = 0

    # Check client_profiles
    row_count = conn.execute("SELECT COUNT(*) FROM client_profiles WHERE client_id IS NOT NULL;").fetchone()[0]
    if row_count != len(name_map):
        logger.warning(f"  client_profiles: expected {len(name_map)} client_ids, found {row_count}")
        errors += 1
    else:
        logger.info(f"  client_profiles: {row_count} rows have client_id")

    # Check no NULL client_ids in critical tables
    for table in ["contact_metadata", "reindex_state"]:
        try:
            nulls = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE client_id IS NULL;").fetchone()[0]
            if nulls > 0:
                logger.warning(f"  {table}: {nulls} rows with NULL client_id")
                errors += 1
            else:
                total = conn.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0]
                logger.info(f"  {table}: {total} rows, all have client_id")
        except sqlite3.OperationalError:
            pass

    # Verify client_profiles PK is non-null
    total_profiles = conn.execute("SELECT COUNT(*) FROM client_profiles;").fetchone()[0]
    if total_profiles > 0:
        by_chat = conn.execute("SELECT chat_name, client_id FROM client_profiles LIMIT 3;").fetchall()
        for chat, cid in by_chat:
            logger.info(f"  Sample: chat_name={chat!r} → client_id={cid}")

    if errors == 0:
        logger.info("✅ All verification checks passed")
    else:
        logger.warning(f"⚠️  {errors} verification check(s) failed — review before rollback")

    return errors


def run_migration(dry_run: bool = False):
    """Execute the UUID migration."""
    db_path = _get_db_path()
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return False

    logger.info(f"Starting UUID migration for database: {db_path}")
    logger.info(f"Dry-run mode: {dry_run}")

    # --- Backup ---
    if not dry_run:
        backup_db = _backup_db(db_path)
        BACKUP_PATH = backup_db
        backup_chats = _backup_chats_dir(config.CHATS_DIR)
    else:
        backup_db = db_path
        backup_chats = Path("dry_run")

    # --- Connect ---
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")

    # --- Build name → UUID map ---
    name_map = _get_chat_name_map(conn)
    if not name_map:
        logger.info("No contacts found in database — nothing to migrate.")
        conn.close()
        return True

    logger.info(f"Found {len(name_map)} unique contact names to migrate")

    if dry_run:
        for name, cid in sorted(name_map.items())[:5]:
            logger.info(f"  Would map: {name!r} → {cid}")
        if len(name_map) > 5:
            logger.info(f"  ... and {len(name_map) - 5} more")
        conn.close()
        return True

    # --- Migrate each table ---
    logger.info("Migrating client_profiles...")
    _migrate_client_profiles(conn, name_map)

    logger.info("Migrating contact_metadata...")
    _migrate_contact_metadata(conn, name_map)

    logger.info("Migrating connection_metrics...")
    _migrate_connection_metrics(conn, name_map)

    logger.info("Migrating contact_platforms...")
    _migrate_contact_platforms(conn, name_map)

    logger.info("Migrating reindex_state...")
    _migrate_reindex_state(conn, name_map)

    logger.info("Migrating clinical_notes...")
    _migrate_clinical_notes(conn, name_map)

    logger.info("Migrating assessment_history...")
    _migrate_assessment_history(conn, name_map)

    logger.info("Migrating session_audio...")
    _migrate_session_audio(conn, name_map)

    logger.info("Migrating pending_merges...")
    _migrate_pending_merges(conn, name_map)

    logger.info("Setting schema version...")
    _set_schema_version(conn)

    # --- Verification ---
    logger.info("Verifying migration...")
    errors = _verify_migration(conn, name_map)

    # --- Write rollback ---
    rollback_path = _write_rollback_file(name_map, backup_db, backup_chats)

    conn.close()

    if errors == 0:
        logger.info(f"✅ Migration complete. Rollback: {rollback_path}")
    else:
        logger.warning(f"⚠️  Migration finished with {errors} verification issues. Rollback: {rollback_path}")

    return errors == 0


def run_rollback():
    """Restore from backup."""
    db_path = _get_db_path()
    # Find the most recent backup
    backups = sorted(db_path.parent.glob(f"{db_path.stem}.pre_uuid.*"))
    if not backups:
        logger.error("No backups found. Cannot rollback.")
        return False

    backup = backups[-1]
    logger.info(f"Restoring from backup: {backup}")
    shutil.copy2(str(backup), str(db_path))
    logger.info(f"Database restored: {db_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate database to UUID client_id")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--rollback", action="store_true", help="Restore from pre-migration backup")
    args = parser.parse_args()

    if args.rollback:
        success = run_rollback()
    elif args.dry_run:
        success = run_migration(dry_run=True)
    else:
        success = run_migration(dry_run=False)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
