"""Print every table in a database: its columns, then all of its rows.

Usage (from the project root):

    python show_tables.py demo.db
    python show_tables.py expense_tracker.db

The database is opened read-only, so this script can never change your data.
Money columns are shown exactly as stored: in paise (100 paise = 1 rupee).
"""
import sqlite3
import sys
from pathlib import Path

MAX_WIDTH = 24  # long values are cut off after this many characters


def show_table(conn, name):
    """Print one table: a title, the column names, then every row."""
    # A table name cannot be passed as a "?" placeholder. It is safe to put it into the
    # SQL here only because the names come from the database itself, not from a user.
    columns = [row["name"] for row in conn.execute(f'PRAGMA table_info("{name}")')]
    rows = conn.execute(f'SELECT * FROM "{name}"').fetchall()

    print()
    print("=" * 72)
    print(f"TABLE {name}   ({len(rows)} rows)")
    print("=" * 72)

    # Work out how wide each column needs to be, so the table lines up.
    widths = []
    for column in columns:
        longest = max([len(column)] + [len(str(row[column])) for row in rows])
        widths.append(min(longest, MAX_WIDTH))

    def line(values):
        cells = [str(value)[:width].ljust(width) for value, width in zip(values, widths)]
        return "  ".join(cells)

    print(line(columns))
    print(line(["-" * width for width in widths]))
    for row in rows:
        print(line([row[column] for column in columns]))
    if not rows:
        print("(empty)")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "expense-tracker.db"
    if not Path(path).is_file():
        sys.exit(f"No database file found at {path}")
    # mode=ro opens the file read-only.
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    names = [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    for name in names:
        show_table(conn, name)
    conn.close()


main()
