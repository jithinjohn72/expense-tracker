import pytest

from core.plan import create_plan
from core.transactions import (
    add_credit,
    add_expense,
    category_totals,
    daily_totals,
    delete_transaction,
    list_transactions,
    update_transaction,
)

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

def test_category_is_trimmed_and_lowercased(conn):
    plan_id = make_plan(conn)
    row = get_row(conn, add_expense(conn, plan_id, "2026-11-02", 100, "", "  Food "))
    assert row["category"] == "food"


def test_blank_category_becomes_uncategorised(conn):
    plan_id = make_plan(conn)
    row = get_row(conn, add_expense(conn, plan_id, "2026-11-02", 100, "", "   "))
    assert row["category"] == "uncategorised"


def test_list_returns_newest_first(conn):
    plan_id = make_plan(conn)
    add_expense(conn, plan_id, "2026-11-02", 100, "older")
    add_expense(conn, plan_id, "2026-11-09", 200, "newer")
    names = [row["description"] for row in list_transactions(conn, plan_id)]
    assert names == ["newer", "older"]


def test_list_can_show_a_single_day(conn):
    plan_id = make_plan(conn)
    add_expense(conn, plan_id, "2026-11-02", 100, "a")
    add_expense(conn, plan_id, "2026-11-03", 200, "b")
    rows = list_transactions(conn, plan_id, "2026-11-03")
    assert [row["description"] for row in rows] == ["b"]


def test_list_leaves_out_other_cycles(conn):
    first = make_plan(conn)
    second = create_plan(conn, "2026-12-01", 5000000)
    add_expense(conn, second, "2026-12-02", 100)
    assert list_transactions(conn, first) == []


def test_daily_totals_add_up_each_day(conn):
    plan_id = make_plan(conn)
    add_expense(conn, plan_id, "2026-11-02", 100)
    add_expense(conn, plan_id, "2026-11-02", 250)
    add_expense(conn, plan_id, "2026-11-05", 400)
    assert daily_totals(conn, plan_id) == {"2026-11-02": 350, "2026-11-05": 400}


def test_daily_totals_ignore_credits(conn):
    plan_id = make_plan(conn)
    add_credit(conn, plan_id, "2026-11-02", 999)
    assert daily_totals(conn, plan_id) == {}


def test_category_totals_are_sorted_biggest_first(conn):
    plan_id = make_plan(conn)
    add_expense(conn, plan_id, "2026-11-02", 100, "", "food")
    add_expense(conn, plan_id, "2026-11-03", 500, "", "clothes")
    add_expense(conn, plan_id, "2026-11-04", 200, "", "Food")
    add_credit(conn, plan_id, "2026-11-05", 999)
    totals = category_totals(conn, plan_id)
    assert totals == {"clothes": 500, "food": 300}
    assert list(totals) == ["clothes", "food"]
    
def test_delete_removes_the_entry(conn):
    plan_id = make_plan(conn)
    keep = add_expense(conn, plan_id, "2026-11-02", 100)
    mistake = add_expense(conn, plan_id, "2026-11-02", 5000)
    delete_transaction(conn, mistake)
    assert [row["id"] for row in list_transactions(conn, plan_id)] == [keep]
    assert daily_totals(conn, plan_id) == {"2026-11-02": 100}


def test_deleting_an_unknown_entry_is_rejected(conn):
    with pytest.raises(ValueError):
        delete_transaction(conn, 999)


def test_update_changes_only_what_is_given(conn):
    plan_id = make_plan(conn)
    txn_id = add_expense(conn, plan_id, "2026-11-02", 5000, "lunch", "food")
    update_transaction(conn, txn_id, amount_paise=500)
    row = get_row(conn, txn_id)
    assert row["amount_paise"] == 500
    assert row["description"] == "lunch"
    assert row["category"] == "food"


def test_update_can_change_the_note_and_category(conn):
    plan_id = make_plan(conn)
    txn_id = add_expense(conn, plan_id, "2026-11-02", 500, "lunch", "food")
    update_transaction(conn, txn_id, description="  dinner  ", category=" Eating Out ")
    row = get_row(conn, txn_id)
    assert row["description"] == "dinner"
    assert row["category"] == "eating out"


def test_update_rejects_a_bad_amount_or_unknown_entry(conn):
    plan_id = make_plan(conn)
    txn_id = add_expense(conn, plan_id, "2026-11-02", 500)
    with pytest.raises(ValueError):
        update_transaction(conn, txn_id, amount_paise=0)
    with pytest.raises(ValueError):
        update_transaction(conn, 999, amount_paise=100)