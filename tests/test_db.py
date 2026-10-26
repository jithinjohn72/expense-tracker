import sqlite3
import pytest

from core.db import get_connection, init_db

@pytest.fixture
def conn():
    connection = get_connection(':memory:')
    init_db(connection)
    yield connection
    connection.close()
    
def table_names(conn):
    rows = conn.execute("SELECT name from sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlit_%'").fetchall()
    return {row["name"] for row in rows}

    
def test_all_tables_are_created(conn):
    assert table_names(conn) == {"monthly_plan", "fixed_items", "transactions", "goals"}

def test_db_can_run_twice(conn):
    init_db(conn)
    assert len(table_names(conn)) == 4
    
def test_negative_salary_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO monthly_plan (cycle_start, cycle_end, salary_paise) "
            "VALUES ('2026-11-01', '2026-11-30', -100)"
        )
        
def test_transaction_needs_a_valid_plan(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO transactions (plan_id, txn_date, amount_paise, direction) "
            "VALUES (999, '2026-11-02', 25000, 'debit')"
        )