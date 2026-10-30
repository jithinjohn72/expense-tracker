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
    return _add_transaction(conn, plan_id, txn_date, amount_paise, "debit", description, category)


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