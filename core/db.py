import sqlite3
from pathlib import Path

SCHEMA_FILE = Path(__file__).with_name("schema.sql")

def get_connection(db_path :str = "expense-tracker.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(conn :sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
    conn.commit()