import pytest

from core.plan import create_plan, get_plan, set_savings_goal


def test_create_plan_stores_dates_and_amounts(conn):
    plan_id = create_plan(conn, "2026-11-01", 5000000, 500000)
    plan = get_plan(conn, plan_id)
    assert plan["cycle_start"] == "2026-11-01"
    assert plan["cycle_end"] == "2026-11-30"
    assert plan["salary_paise"] == 5000000
    assert plan["savings_goal_paise"] == 500000


def test_savings_goal_defaults_to_zero(conn):
    plan_id = create_plan(conn, "2026-11-01", 5000000)
    assert get_plan(conn, plan_id)["savings_goal_paise"] == 0


def test_duplicate_cycle_is_rejected(conn):
    create_plan(conn, "2026-11-01", 5000000)
    with pytest.raises(ValueError):
        create_plan(conn, "2026-11-01", 6000000)


def test_bad_date_is_rejected(conn):
    with pytest.raises(ValueError):
        create_plan(conn, "01-11-2026", 5000000)


def test_salary_day_above_28_is_rejected(conn):
    with pytest.raises(ValueError):
        create_plan(conn, "2026-10-30", 5000000)


def test_zero_or_negative_salary_is_rejected(conn):
    with pytest.raises(ValueError):
        create_plan(conn, "2026-11-01", 0)
    with pytest.raises(ValueError):
        create_plan(conn, "2026-11-01", -5)


def test_negative_savings_goal_is_rejected(conn):
    with pytest.raises(ValueError):
        create_plan(conn, "2026-11-01", 5000000, -1)


def test_fractional_salary_is_rejected(conn):
    with pytest.raises(ValueError):
        create_plan(conn, "2026-11-01", 5000000.5)


def test_get_unknown_plan_is_rejected(conn):
    with pytest.raises(ValueError):
        get_plan(conn, 999)


def test_savings_goal_can_be_changed(conn):
    plan_id = create_plan(conn, "2026-11-01", 5000000, 500000)
    set_savings_goal(conn, plan_id, 800000)
    assert get_plan(conn, plan_id)["savings_goal_paise"] == 800000


def test_savings_goal_can_be_set_to_zero(conn):
    plan_id = create_plan(conn, "2026-11-01", 5000000, 500000)
    set_savings_goal(conn, plan_id, 0)
    assert get_plan(conn, plan_id)["savings_goal_paise"] == 0


def test_negative_savings_goal_change_is_rejected(conn):
    plan_id = create_plan(conn, "2026-11-01", 5000000)
    with pytest.raises(ValueError):
        set_savings_goal(conn, plan_id, -100)


def test_changing_goal_of_unknown_plan_is_rejected(conn):
    with pytest.raises(ValueError):
        set_savings_goal(conn, 999, 100)

