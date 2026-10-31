import pytest

from core.fixed_items import add_fixed_item
from core.limits import daily_limit
from core.plan import create_plan
from core.transactions import add_credit, add_expense
from core.goals import add_goal


def make_cycle(conn):
    """Pool of 18,000: salary 50,000 - rent 15,000 - EMI 5,000 - RD 5,000 - savings 7,000."""
    plan_id = create_plan(conn, "2026-11-01", 5000000, 700000)
    add_fixed_item(conn, "Rent", "expense", 1500000)
    add_fixed_item(conn, "Phone EMI", "expense", 500000)
    add_fixed_item(conn, "RD", "deposit", 500000)
    return plan_id


def test_day_one_limit_is_the_pool_divided_by_the_days(conn):
    result = daily_limit(conn, make_cycle(conn), "2026-11-01")
    assert result["limit"] == 60000  # 600.00
    assert result["days_left"] == 30


def test_unspent_money_rolls_into_the_next_day(conn):
    plan_id = make_cycle(conn)
    add_expense(conn, plan_id, "2026-11-01", 40000)
    assert daily_limit(conn, plan_id, "2026-11-02")["limit"] == 60689  # 606.89


def test_overspending_lowers_the_next_limit(conn):
    plan_id = make_cycle(conn)
    add_expense(conn, plan_id, "2026-11-01", 40000)
    add_expense(conn, plan_id, "2026-11-02", 90000)
    assert daily_limit(conn, plan_id, "2026-11-03")["limit"] == 59642  # 596.42


def test_todays_spending_does_not_change_todays_limit(conn):
    plan_id = make_cycle(conn)
    add_expense(conn, plan_id, "2026-11-01", 40000)
    result = daily_limit(conn, plan_id, "2026-11-01")
    assert result["limit"] == 60000
    assert result["spent_today"] == 40000
    assert result["left_today"] == 20000


def test_extra_credit_raises_the_limit_from_that_day_on(conn):
    plan_id = make_cycle(conn)
    add_credit(conn, plan_id, "2026-11-11", 300000)
    assert daily_limit(conn, plan_id, "2026-11-11")["limit"] == 105000  # 1,050.00
    assert daily_limit(conn, plan_id, "2026-11-12")["limit"] == 2100000 // 19


def test_days_before_the_credit_do_not_change(conn):
    plan_id = make_cycle(conn)
    add_credit(conn, plan_id, "2026-11-11", 300000)
    assert daily_limit(conn, plan_id, "2026-11-10")["limit"] == 1800000 // 21


def test_a_used_up_pool_gives_a_zero_limit_and_the_overspend(conn):
    plan_id = make_cycle(conn)
    add_expense(conn, plan_id, "2026-11-01", 1900000)
    result = daily_limit(conn, plan_id, "2026-11-02")
    assert result["limit"] == 0
    assert result["over_budget_by"] == 100000


def test_last_day_of_the_cycle_uses_one_day_left(conn):
    plan_id = make_cycle(conn)
    result = daily_limit(conn, plan_id, "2026-11-30")
    assert result["days_left"] == 1
    assert result["limit"] == 1800000


def test_date_outside_the_cycle_is_rejected(conn):
    plan_id = make_cycle(conn)
    with pytest.raises(ValueError):
        daily_limit(conn, plan_id, "2026-12-01")


def test_unknown_plan_is_rejected(conn):
    with pytest.raises(ValueError):
        daily_limit(conn, 999, "2026-11-01")
        
def test_a_goal_set_aside_lowers_the_limit(conn):
    plan_id = make_cycle(conn)
    add_goal(conn, "Phone", 1200000, "2027-04-10")  # 2,000 reserved each cycle
    assert daily_limit(conn, plan_id, "2026-11-01")["limit"] == 1600000 // 30