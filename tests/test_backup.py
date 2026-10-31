import sqlite3

import pytest

from core.backup import backup_database, restore_database
from core.db import get_connection, init_db
from core.fixed_items import add_fixed_item, list_fixed_items


def names(connection):
    return [row["name"] for row in list_fixed_items(connection)]


def test_a_backup_can_be_restored_into_a_new_database(conn, tmp_path):
    add_fixed_item(conn, "Rent", "expense", 1500000)
    backup_file = str(tmp_path / "backup.db")
    backup_database(conn, backup_file)
    fresh = get_connection(":memory:")
    init_db(fresh)
    restore_database(fresh, backup_file)
    assert names(fresh) == ["Rent"]
    fresh.close()


def test_restore_replaces_what_is_there_now(conn, tmp_path):
    add_fixed_item(conn, "Rent", "expense", 1500000)
    backup_file = str(tmp_path / "backup.db")
    backup_database(conn, backup_file)
    add_fixed_item(conn, "Gym", "expense", 100000)
    restore_database(conn, backup_file)
    assert names(conn) == ["Rent"]


def test_restore_rejects_a_missing_file(conn, tmp_path):
    with pytest.raises(ValueError):
        restore_database(conn, str(tmp_path / "nothing_here.db"))


def test_restore_rejects_a_database_without_our_tables(conn, tmp_path):
    other = tmp_path / "other.db"
    sqlite3.connect(str(other)).close()
    with pytest.raises(ValueError):
        restore_database(conn, str(other))


def test_restore_rejects_a_file_that_is_not_a_database(conn, tmp_path):
    junk = tmp_path / "junk.db"
    junk.write_text("this is not a database")
    with pytest.raises(ValueError):
        restore_database(conn, str(junk))