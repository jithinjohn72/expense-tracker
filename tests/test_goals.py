import pytest

from core.fixed_items import add_fixed_item
from core.goals import (
    add_goal,
    add_to_goal,
    get_goal,
    goal_set_aside,
    list_goals,
    set_goal_active,
    total_set_asides,
)
from core.limits import daily_limit
from core.plan import create_plan
from core.summary import cycle_summary


def test_add_goal_stores_the_goal(conn):
    goal = get_goal(conn, add_goal(conn, "Phone", 1200000, "2027-04-10", 100000))
    assert goal["name"] == "Phone"
    assert goal["price_paise"] == 1200000
    assert goal["saved_paise"] == 100000
    assert goal["target_date"] == "2027-04-10"
    assert goal["active"] == 1


def test_goal_name_is_trimmed_and_cannot_be_blank(conn):
    assert get_goal(conn, add_goal(conn, "  Phone  ", 100, "2027-04-10"))["name"] == "Phone"
    with pytest.raises(ValueError):
        add_goal(conn, "   ", 100, "2027-04-10")


def test_price_must_be_a_positive_whole_number(conn):
    for bad_price in [0, -5, 10.5]:
        with pytest.raises(ValueError):
            add_goal(conn, "Phone", bad_price, "2027-04-10")


def test_saved_amount_cannot_exceed_the_price(conn):
    with pytest.raises(ValueError):
        add_goal(conn, "Phone", 1000, "2027-04-10", 2000)


def test_bad_target_date_is_rejected(conn):
    with pytest.raises(ValueError):
        add_goal(conn, "Phone", 1000, "10-04-2027")


def test_add_to_goal_tops_up_the_saved_amount(conn):
    goal_id = add_goal(conn, "Phone", 1200000, "2027-04-10", 100000)
    add_to_goal(conn, goal_id, 50000)
    assert get_goal(conn, goal_id)["saved_paise"] == 150000


def test_saved_amount_is_capped_at_the_price(conn):
    goal_id = add_goal(conn, "Phone", 1000, "2027-04-10", 900)
    add_to_goal(conn, goal_id, 500)
    assert get_goal(conn, goal_id)["saved_paise"] == 1000


def test_unknown_goal_is_rejected(conn):
    with pytest.raises(ValueError):
        get_goal(conn, 999)


def test_list_hides_inactive_goals_and_sorts_by_date(conn):
    add_goal(conn, "Laptop", 100, "2027-09-01")
    add_goal(conn, "Phone", 100, "2027-03-01")
    old = add_goal(conn, "Old", 100, "2027-01-01")
    set_goal_active(conn, old, False)
    assert [g["name"] for g in list_goals(conn)] == ["Phone", "Laptop"]
    assert len(list_goals(conn, active_only=False)) == 3


def test_set_aside_splits_the_price_over_the_cycles(conn):
    goal = get_goal(conn, add_goal(conn, "Phone", 1200000, "2027-04-10"))
    assert goal_set_aside(goal, "2026-11-01") == 200000  # 6 cycles


def test_set_aside_rounds_up(conn):
    goal = get_goal(conn, add_goal(conn, "Phone", 1000100, "2027-01-15"))
    assert goal_set_aside(goal, "2026-11-01") == 333367  # 3 cycles


def test_money_already_saved_reduces_the_set_aside(conn):
    goal = get_goal(conn, add_goal(conn, "Phone", 1200000, "2027-04-10", 600000))
    assert goal_set_aside(goal, "2026-11-01") == 100000


def test_a_fully_funded_goal_needs_nothing(conn):
    goal = get_goal(conn, add_goal(conn, "Phone", 1000, "2027-04-10", 1000))
    assert goal_set_aside(goal, "2026-11-01") == 0


def test_an_overdue_goal_asks_for_everything_now(conn):
    goal = get_goal(conn, add_goal(conn, "Phone", 500000, "2026-09-05"))
    assert goal_set_aside(goal, "2026-11-01") == 500000


def test_total_set_asides_adds_active_goals_only(conn):
    plan_id = create_plan(conn, "2026-11-01", 5000000)
    add_goal(conn, "Phone", 1200000, "2027-04-10")
    skipped = add_goal(conn, "Laptop", 6000000, "2027-04-10")
    set_goal_active(conn, skipped, False)
    assert total_set_asides(conn, plan_id) == 200000


def test_set_asides_lower_the_pool_and_the_daily_limit(conn):
    plan_id = create_plan(conn, "2026-11-01", 5000000)
    add_goal(conn, "Phone", 1200000, "2027-04-10")
    summary = cycle_summary(conn, plan_id)
    assert summary["set_asides"] == 200000
    assert summary["spendable_pool"] == 4800000
    assert daily_limit(conn, plan_id, "2026-11-01")["limit"] == 160000
    