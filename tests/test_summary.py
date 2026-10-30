from core.fixed_items import add_fixed_item, set_fixed_active
from core.plan import create_plan, set_savings_goal
from core.summary import cycle_summary
from core.transactions import add_credit, add_expense


def make_cycle(conn):
    """Salary 50,000, savings goal 5,000, rent 15,000, EMI 5,000, RD 5,000 (all in paise)."""
    plan_id = create_plan(conn, "2026-11-01", 5000000, 500000)
    add_fixed_item(conn, "Rent", "expense", 1500000)
    add_fixed_item(conn, "Phone EMI", "expense", 500000)
    add_fixed_item(conn, "RD", "deposit", 500000)
    return plan_id


def test_pool_matches_the_worked_example(conn):
    summary = cycle_summary(conn, make_cycle(conn))
    assert summary["salary"] == 5000000
    assert summary["fixed_expenses"] == 2000000
    assert summary["locked_deposits"] == 500000
    assert summary["reserved_savings"] == 500000
    assert summary["spendable_pool"] == 2000000
    assert summary["left_to_spend"] == 2000000
    assert summary["over_planned"] is False


def test_extra_credit_goes_to_the_pool(conn):
    plan_id = make_cycle(conn)
    add_credit(conn, plan_id, "2026-11-11", 300000)
    summary = cycle_summary(conn, plan_id)
    assert summary["extra_credits"] == 300000
    assert summary["spendable_pool"] == 2300000
    assert summary["locked_deposits"] == 500000  # a credit never becomes a deposit


def test_spending_reduces_what_is_left_but_not_the_pool(conn):
    plan_id = make_cycle(conn)
    add_expense(conn, plan_id, "2026-11-01", 40000)
    add_expense(conn, plan_id, "2026-11-02", 90000)
    summary = cycle_summary(conn, plan_id)
    assert summary["spent"] == 130000
    assert summary["spendable_pool"] == 2000000
    assert summary["left_to_spend"] == 1870000


def test_extra_credit_and_spending_together(conn):
    plan_id = make_cycle(conn)
    add_credit(conn, plan_id, "2026-11-11", 300000)
    add_expense(conn, plan_id, "2026-11-01", 40000)
    add_expense(conn, plan_id, "2026-11-02", 90000)
    assert cycle_summary(conn, plan_id)["left_to_spend"] == 2170000


def test_a_new_deposit_is_locked_and_lowers_the_pool(conn):
    plan_id = make_cycle(conn)
    add_fixed_item(conn, "FD", "deposit", 100000)
    summary = cycle_summary(conn, plan_id)
    assert summary["locked_deposits"] == 600000
    assert summary["spendable_pool"] == 1900000


def test_raising_the_savings_goal_lowers_the_pool(conn):
    plan_id = make_cycle(conn)
    set_savings_goal(conn, plan_id, 800000)
    summary = cycle_summary(conn, plan_id)
    assert summary["reserved_savings"] == 800000
    assert summary["spendable_pool"] == 1700000


def test_inactive_fixed_items_are_left_out(conn):
    plan_id = make_cycle(conn)
    emi = conn.execute("SELECT id FROM fixed_items WHERE name = 'Phone EMI'").fetchone()["id"]
    set_fixed_active(conn, emi, False)
    summary = cycle_summary(conn, plan_id)
    assert summary["fixed_expenses"] == 1500000
    assert summary["spendable_pool"] == 2500000


def test_over_planned_cycle_is_flagged(conn):
    plan_id = create_plan(conn, "2026-11-01", 100000)
    add_fixed_item(conn, "Rent", "expense", 500000)
    summary = cycle_summary(conn, plan_id)
    assert summary["spendable_pool"] == -400000
    assert summary["over_planned"] is True


def test_transactions_of_another_cycle_do_not_leak(conn):
    first = make_cycle(conn)
    second = create_plan(conn, "2026-12-01", 5000000)
    add_credit(conn, second, "2026-12-05", 999999)
    add_expense(conn, second, "2026-12-06", 111111)
    summary = cycle_summary(conn, first)
    assert summary["extra_credits"] == 0
    assert summary["spent"] == 0