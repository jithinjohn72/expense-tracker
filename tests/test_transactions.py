import pytest

from core.plan import create_plan
from core.transactions import add_credit, add_expense


def make_plan(conn):
    return create_plan(conn, "2026-11-01", 5000000)


def get_row(conn, txn_id):
    return conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()


def test_expense_is_stored_as_a_debit(conn):
    plan_id = make_plan(conn)
    txn_id = add_expense(conn, plan_id, "2026-11-02", 25000, "  lunch  ", "food")
    row = get_row(conn, txn_id)
    assert row["direction"] == "debit"
    assert row["amount_paise"] == 25000
    assert row["description"] == "lunch"
    assert row["category"] == "food"
    assert row["plan_id"] == plan_id


def test_credit_is_stored_as_a_credit(conn):
    plan_id = make_plan(conn)
    txn_id = add_credit(conn, plan_id, "2026-11-11", 300000, "freelance work")
    row = get_row(conn, txn_id)
    assert row["direction"] == "credit"
    assert row["category"] == "extra income"


def test_expense_defaults_to_uncategorised(conn):
    plan_id = make_plan(conn)
    row = get_row(conn, add_expense(conn, plan_id, "2026-11-02", 100))
    assert row["category"] == "uncategorised"
    assert row["description"] == ""


def test_date_before_the_cycle_is_rejected(conn):
    plan_id = make_plan(conn)
    with pytest.raises(ValueError):
        add_expense(conn, plan_id, "2026-10-31", 100)


def test_date_after_the_cycle_is_rejected(conn):
    plan_id = make_plan(conn)
    with pytest.raises(ValueError):
        add_expense(conn, plan_id, "2026-12-01", 100)


def test_first_and_last_day_of_the_cycle_are_allowed(conn):
    plan_id = make_plan(conn)
    add_expense(conn, plan_id, "2026-11-01", 100)
    add_expense(conn, plan_id, "2026-11-30", 100)


def test_unknown_plan_is_rejected(conn):
    with pytest.raises(ValueError):
        add_expense(conn, 999, "2026-11-02", 100)


def test_zero_and_negative_amounts_are_rejected(conn):
    plan_id = make_plan(conn)
    with pytest.raises(ValueError):
        add_expense(conn, plan_id, "2026-11-02", 0)
    with pytest.raises(ValueError):
        add_credit(conn, plan_id, "2026-11-02", -50)


def test_bad_date_text_is_rejected(conn):
    plan_id = make_plan(conn)
    with pytest.raises(ValueError):
        add_expense(conn, plan_id, "2 Nov 2026", 100)
