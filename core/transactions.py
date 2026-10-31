"""Money moving in and out during a pay cycle."""
import sqlite3

from core.cycle import parse_date
from core.money import check_paise
from core.plan import get_plan


def _add_transaction(
    conn: sqlite3.Connection,
    plan_id: int,
    txn_date: str,
    amount_paise: int,
    direction: str,
    description: str,
    category: str,
) -> int:
    plan = get_plan(conn, plan_id)
    day = parse_date(txn_date).isoformat()
    if not (plan["cycle_start"] <= day <= plan["cycle_end"]):
        raise ValueError(
            f"Date {day} is outside this cycle "
            f"({plan['cycle_start']} to {plan['cycle_end']})."
        )
    check_paise(amount_paise, "Amount")
    cursor = conn.execute(
        "INSERT INTO transactions "
        "(plan_id, txn_date, amount_paise, direction, description, category) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (plan_id, day, amount_paise, direction, description.strip(), category),
    )
    conn.commit()
    return cursor.lastrowid


def add_expense(
    conn: sqlite3.Connection,
    plan_id: int,
    txn_date: str,
    amount_paise: int,
    description: str = "",
    category: str = "uncategorised",
) -> int:
    """Record everyday spending (a debit) and return its id."""
    clean_category = category.strip().lower() or "uncategorised"
    return _add_transaction(
        conn, plan_id, txn_date, amount_paise, "debit", description, clean_category
    )

def add_credit(
    conn: sqlite3.Connection,
    plan_id: int,
    txn_date: str,
    amount_paise: int,
    description: str = "",
) -> int:
    """Record extra money received during the cycle. It goes to the spendable pool."""
    return _add_transaction(
        conn, plan_id, txn_date, amount_paise, "credit", description, "extra income"
    )
    
def list_transactions(conn: sqlite3.Connection, plan_id: int, day: str = None) -> list:
    """Return a cycle's transactions, newest first. Pass day to see just that date."""
    if day is None:
        return conn.execute(
            "SELECT * FROM transactions WHERE plan_id = ? ORDER BY txn_date DESC, id DESC",
            (plan_id,),
        ).fetchall()
    day_text = parse_date(day).isoformat()
    return conn.execute(
        "SELECT * FROM transactions WHERE plan_id = ? AND txn_date = ? ORDER BY id DESC",
        (plan_id, day_text),
    ).fetchall()


def daily_totals(conn: sqlite3.Connection, plan_id: int) -> dict:
    """Return {date: total spent that day} for a cycle. Credits are not included."""
    rows = conn.execute(
        "SELECT txn_date, SUM(amount_paise) AS total FROM transactions "
        "WHERE plan_id = ? AND direction = 'debit' "
        "GROUP BY txn_date ORDER BY txn_date",
        (plan_id,),
    ).fetchall()
    return {row["txn_date"]: row["total"] for row in rows}


def category_totals(conn: sqlite3.Connection, plan_id: int) -> dict:
    """Return {category: total spent} for a cycle, biggest first. Credits are not included."""
    rows = conn.execute(
        "SELECT category, SUM(amount_paise) AS total FROM transactions "
        "WHERE plan_id = ? AND direction = 'debit' "
        "GROUP BY category ORDER BY total DESC, category",
        (plan_id,),
    ).fetchall()
    return {row["category"]: row["total"] for row in rows}