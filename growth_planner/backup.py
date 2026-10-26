"""Consistent SQLite backups and a deliberate, validated offline restore."""

from datetime import datetime
from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from growth_planner.database import SCHEMA, open_database


def schema_signature(database):
    return sorted((row[0], row[1], row[2]) for row in database.execute(
        "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))


def validate_backup(path):
    try:
        with closing(sqlite3.connect(":memory:")) as reference:
            reference.executescript(SCHEMA)
            expected = schema_signature(reference)
        source = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
        try:
            if source.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Backup integrity check failed.")
            if schema_signature(source) != expected:
                raise ValueError("Backup schema does not match this application version.")
            if source.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Backup contains broken record references.")
            if source.execute("SELECT value FROM app_meta WHERE key='schema_version'").fetchone() != ("2",):
                raise ValueError("Unsupported backup version.")
            if not source.execute("SELECT 1 FROM users WHERE role='faculty'").fetchone():
                raise ValueError("Backup has no faculty account.")
        finally:
            source.close()
    except sqlite3.DatabaseError:
        raise ValueError("This file is not a valid Student Growth Planner backup.")


def create_backup(planner, token):
    temporary_root = planner.database_file.parent / "backups"
    temporary_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=temporary_root) as folder:
        target = Path(folder) / "backup.db"
        with open_database(planner.database_file) as db:
            actor = planner._actor(db, token, faculty=True)
            planner._audit(db, actor["username"], "create backup", "database")
        # A dedicated source connection allows SQLite's backup API to take a consistent snapshot.
        with open_database(planner.database_file) as source:
            with closing(sqlite3.connect(target)) as destination:
                with destination:
                    source.backup(destination)
                    destination.execute("DELETE FROM sessions")
        validate_backup(target)
        return target.read_bytes()


def restore_backup(planner, token, backup_path):
    """Caller must stop browser/API/desktop before running this maintenance action."""
    backup_path = Path(backup_path).resolve()
    if backup_path == planner.database_file.resolve():
        raise ValueError("Select a separate backup file.")
    with open_database(planner.database_file) as db:
        planner._actor(db, token, faculty=True)
    validate_backup(backup_path)
    safety = planner.database_file.parent / "backups"
    safety.mkdir(parents=True, exist_ok=True)
    safety_path = safety / ("before_restore_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".db")
    safety_path.write_bytes(create_backup(planner, token))
    # SQLite handles the replacement transaction; a failed copy rolls back.
    source = sqlite3.connect(backup_path.as_uri() + "?mode=ro", uri=True)
    try:
        with open_database(planner.database_file) as destination:
            source.backup(destination)
            destination.execute("DELETE FROM sessions")
            planner._audit(destination, "maintenance", "restore backup", backup_path.name)
    finally:
        source.close()
    return safety_path
