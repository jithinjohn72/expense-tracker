"""Back up and restore the whole database."""
import sqlite3
from pathlib import Path

from core.db import init_db

REQUIRED_TABLES = {"monthly_plan", "fixed_items", "transactions", "goals"}


def backup_database(conn: sqlite3.Connection, dest_path: str) -> None:
    """Copy the whole database into a file at dest_path."""
    destination = sqlite3.connect(dest_path)
    try:
        conn.backup(destination)
    finally:
        destination.close()


def restore_database(conn: sqlite3.Connection, source_path: str) -> None:
    """Replace everything in the open database with the contents of a backup file."""
    if not Path(source_path).is_file():
        raise ValueError(f"No backup file found at {source_path}.")
    source = sqlite3.connect(source_path)
    try:
        try:
            names = {
                row[0]
                for row in source.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
        except sqlite3.DatabaseError:
            raise ValueError("That file is not a valid backup.") from None
        if not REQUIRED_TABLES <= names:
            raise ValueError("That file is not a valid backup.")
        source.backup(conn)
    finally:
        source.close()
    init_db(conn)