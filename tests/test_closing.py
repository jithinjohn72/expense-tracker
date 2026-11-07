import pytest

from core.closing import close_cycle, savings_totals
from core.fixed_items import add_fixed_item
from core.goals import add_goal, get_goal
from core.limits import daily_limit
from core.plan import create_plan, set_salary, set_savings_goal
from core.summary import cycle_summary
from core.transactions import add_expense, delete_transaction, update_transaction


def make_cycle(conn):
    """Salary 50,000, savings goal 5,000, rent 20,000, RD 5,000: a pool of 20,000."""
    plan_id = create_plan(conn, "2026-11-01", 5000000, 500000)
    add_fixed_item(conn, "Rent", "expense", 2000000)
    add_fixed_item(conn, "RD", "deposit", 500000)
    return plan_id


def spend_and_finish(conn, spent_paise):
    """Make the cycle, spend an amount in it, and return its id."""
    plan_id = make_cycle(conn)
    add_expense(conn, plan_id, "2026-11-10", spent_paise)
    return plan_id


def test_a_running_cycle_cannot_be_closed(conn):
    plan_id = make_cycle(conn)
    with pytest.raises(ValueError):
        close_cycle(conn, plan_id, "2026-11-15")
    with pytest.raises(ValueError):
        close_cycle(conn, plan_id, "2026-11-30")


def test_closing_reports_the_leftover_and_what_was_saved(conn):
    plan_id = spend_and_finish(conn, 1500000)
    result = close_cycle(conn, plan_id, "2026-12-01")
    assert result == {"leftover": 500000, "action": "savings", "saved_this_cycle": 1000000}


def test_a_cycle_cannot_be_closed_twice(conn):
    plan_id = spend_and_finish(conn, 1500000)
    close_cycle(conn, plan_id, "2026-12-01")
    with pytest.raises(ValueError):
        close_cycle(conn, plan_id, "2026-12-02")


def test_a_closed_cycle_rejects_new_spending(conn):
    plan_id = spend_and_finish(conn, 1500000)
    close_cycle(conn, plan_id, "2026-12-01")
    with pytest.raises(ValueError):
        add_expense(conn, plan_id, "2026-11-20", 100)


def test_a_closed_cycle_rejects_a_savings_goal_change(conn):
    plan_id = spend_and_finish(conn, 1500000)
    close_cycle(conn, plan_id, "2026-12-01")
    with pytest.raises(ValueError):
        set_savings_goal(conn, plan_id, 900000)


def test_a_closed_cycle_keeps_its_numbers_when_fixed_items_change(conn):
    plan_id = spend_and_finish(conn, 1500000)
    close_cycle(conn, plan_id, "2026-12-01")
    add_fixed_item(conn, "Gym", "expense", 100000)
    summary = cycle_summary(conn, plan_id)
    assert summary["fixed_expenses"] == 2000000
    assert summary["left_to_spend"] == 500000


def test_closing_adds_the_set_aside_to_each_goal(conn):
    plan_id = spend_and_finish(conn, 1500000)
    goal_id = add_goal(conn, "Phone", 1200000, "2027-04-10")
    close_cycle(conn, plan_id, "2026-12-01")
    assert get_goal(conn, goal_id)["saved_paise"] == 200000


def test_savings_action_adds_the_leftover_to_total_saved(conn):
    plan_id = spend_and_finish(conn, 1500000)
    close_cycle(conn, plan_id, "2026-12-01", "savings")
    assert savings_totals(conn)["total_saved"] == 1000000


def test_carry_action_moves_the_leftover_to_the_next_pool(conn):
    plan_id = spend_and_finish(conn, 1500000)
    close_cycle(conn, plan_id, "2026-12-01", "carry")
    assert savings_totals(conn)["total_saved"] == 500000  # the goal only
    next_id = create_plan(conn, "2026-12-01", 5000000, 500000)
    summary = cycle_summary(conn, next_id)
    assert summary["carried_in"] == 500000
    assert summary["spendable_pool"] == 2500000
    assert daily_limit(conn, next_id, "2026-12-01")["limit"] == 2500000 // 31


def test_overspending_reduces_total_saved(conn):
    plan_id = spend_and_finish(conn, 2200000)
    result = close_cycle(conn, plan_id, "2026-12-01", "savings")
    assert result["leftover"] == -200000
    assert savings_totals(conn)["total_saved"] == 300000


def test_deposits_are_counted_for_closed_and_open_cycles(conn):
    plan_id = spend_and_finish(conn, 1500000)
    close_cycle(conn, plan_id, "2026-12-01")
    create_plan(conn, "2026-12-01", 5000000)
    totals = savings_totals(conn)
    assert totals["deposits_locked"] == 1000000
    assert totals["total_saved"] == 1000000  # deposits are never mixed into savings


def test_money_in_goals_is_reported_separately(conn):
    plan_id = spend_and_finish(conn, 1500000)
    add_goal(conn, "Phone", 1200000, "2027-04-10")
    close_cycle(conn, plan_id, "2026-12-01")
    assert savings_totals(conn)["saved_for_goals"] == 200000


def test_unknown_leftover_action_is_rejected(conn):
    plan_id = spend_and_finish(conn, 1500000)
    with pytest.raises(ValueError):
        close_cycle(conn, plan_id, "2026-12-01", "spend it")


def test_closing_an_unknown_cycle_is_rejected(conn):
    with pytest.raises(ValueError):
        close_cycle(conn, 999, "2026-12-01")


def test_totals_are_zero_when_nothing_exists(conn):
    assert savings_totals(conn) == {
        "total_saved": 0,
        "deposits_locked": 0,
        "saved_for_goals": 0,
    }


def test_a_closed_cycle_rejects_editing_and_deleting_entries(conn):
    plan_id = make_cycle(conn)
    txn_id = add_expense(conn, plan_id, "2026-11-10", 1500000)
    close_cycle(conn, plan_id, "2026-12-01")
    with pytest.raises(ValueError):
        update_transaction(conn, txn_id, amount_paise=100)
    with pytest.raises(ValueError):
        delete_transaction(conn, txn_id)
        
def test_a_closed_cycle_rejects_a_salary_correction(conn):
    plan_id = spend_and_finish(conn, 1500000)
    close_cycle(conn, plan_id, "2026-12-01")
    with pytest.raises(ValueError):
        set_salary(conn, plan_id, 9999900)
        
