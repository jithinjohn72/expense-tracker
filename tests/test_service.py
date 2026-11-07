import pytest

from core.fixed_items import list_fixed_items
from core.goals import list_goals
from core.plan import create_plan, get_plan
from core.service import (
    add_fixed,
    add_spending_today,
    change_fixed_amount,
    change_salary,
    change_savings_goal,
    cycle_start_for,
    home_view,
    parse_salary_day,
    seed_demo_data,
    setup_view,
    start_cycle,
    switch_fixed,
)
from core.transactions import list_transactions

def test_home_view_is_none_when_no_cycle_covers_today(conn):
    assert home_view(conn, "2026-11-04") is None


def test_seeding_creates_a_cycle_that_covers_today(conn):
    seed_demo_data(conn, "2026-11-04")
    view = home_view(conn, "2026-11-04")
    assert view["plan"]["cycle_start"] == "2026-11-01"
    assert view["plan"]["cycle_end"] == "2026-11-30"


def test_seeding_adds_fixed_items_a_goal_and_past_spending(conn):
    seed_demo_data(conn, "2026-11-04")
    assert [row["name"] for row in list_fixed_items(conn)] == ["RD", "Phone EMI", "Rent"]
    assert len(list_goals(conn)) == 1
    plan_id = home_view(conn, "2026-11-04")["plan"]["id"]
    assert len(list_transactions(conn, plan_id)) == 3  # the 1st, 2nd and 3rd


def test_seeding_on_the_first_adds_no_spending(conn):
    seed_demo_data(conn, "2026-12-01")
    plan_id = home_view(conn, "2026-12-01")["plan"]["id"]
    assert list_transactions(conn, plan_id) == []


def test_seeding_twice_in_the_same_cycle_is_refused(conn):
    seed_demo_data(conn, "2026-11-04")
    with pytest.raises(ValueError):
        seed_demo_data(conn, "2026-11-04")


def test_seeding_a_later_month_keeps_existing_items(conn):
    seed_demo_data(conn, "2026-11-04")
    seed_demo_data(conn, "2026-12-10")
    assert len(list_fixed_items(conn)) == 3
    assert len(list_goals(conn)) == 1


def test_home_view_has_the_limit_the_summary_and_todays_entries(conn):
    seed_demo_data(conn, "2026-11-04")
    view = home_view(conn, "2026-11-04")
    assert view["limit"]["days_left"] == 27
    assert view["summary"]["locked_deposits"] == 500000
    assert view["entries"] == []


def test_adding_spending_from_text_shows_up_in_the_view(conn):
    seed_demo_data(conn, "2026-11-04")
    add_spending_today(conn, "2026-11-04", "250", "lunch", "Food")
    view = home_view(conn, "2026-11-04")
    assert view["limit"]["spent_today"] == 25000
    assert [row["category"] for row in view["entries"]] == ["food"]


def test_blank_note_and_category_are_allowed(conn):
    seed_demo_data(conn, "2026-11-04")
    add_spending_today(conn, "2026-11-04", "99.50")
    entry = home_view(conn, "2026-11-04")["entries"][0]
    assert entry["amount_paise"] == 9950
    assert entry["category"] == "uncategorised"


def test_bad_amount_text_gives_a_plain_error(conn):
    seed_demo_data(conn, "2026-11-04")
    for bad in ["", "abc", "-5", "0"]:
        with pytest.raises(ValueError):
            add_spending_today(conn, "2026-11-04", bad)


def test_spending_without_a_cycle_gives_a_plain_error(conn):
    with pytest.raises(ValueError):
        add_spending_today(conn, "2026-11-04", "100")


def test_home_view_follows_the_date_into_the_next_cycle(conn):
    create_plan(conn, "2026-11-01", 5000000)
    create_plan(conn, "2026-12-01", 6000000)
    assert home_view(conn, "2026-11-20")["summary"]["salary"] == 5000000
    assert home_view(conn, "2026-12-02")["summary"]["salary"] == 6000000

def test_cycle_start_when_the_salary_day_is_the_first():
    assert cycle_start_for("2026-11-04", 1) == "2026-11-01"


def test_cycle_start_is_this_month_once_the_salary_day_has_passed():
    assert cycle_start_for("2026-11-30", 28) == "2026-11-28"
    assert cycle_start_for("2026-11-28", 28) == "2026-11-28"


def test_cycle_start_is_last_month_before_the_salary_day():
    assert cycle_start_for("2026-11-04", 28) == "2026-10-28"


def test_cycle_start_crosses_into_the_previous_year():
    assert cycle_start_for("2027-01-05", 28) == "2026-12-28"


def test_salary_day_must_be_a_whole_number_from_1_to_28():
    assert parse_salary_day(" 15 ") == 15
    for bad in ["", "abc", "0", "29", "-3", "1.5", None]:
        with pytest.raises(ValueError):
            parse_salary_day(bad)


def test_start_cycle_creates_the_cycle_that_covers_today(conn):
    plan_id = start_cycle(conn, "2026-11-10", "1", "50000", "5000")
    plan = get_plan(conn, plan_id)
    assert (plan["cycle_start"], plan["cycle_end"]) == ("2026-11-01", "2026-11-30")
    assert plan["salary_paise"] == 5000000
    assert plan["savings_goal_paise"] == 500000
    assert home_view(conn, "2026-11-10") is not None


def test_a_blank_savings_goal_means_zero(conn):
    plan_id = start_cycle(conn, "2026-11-10", "1", "50000", "  ")
    assert get_plan(conn, plan_id)["savings_goal_paise"] == 0


def test_start_cycle_rejects_a_bad_salary_and_an_overlapping_cycle(conn):
    with pytest.raises(ValueError):
        start_cycle(conn, "2026-11-10", "1", "")
    with pytest.raises(ValueError):
        start_cycle(conn, "2026-11-10", "1", "abc")
    start_cycle(conn, "2026-11-10", "1", "50000")
    with pytest.raises(ValueError):
        start_cycle(conn, "2026-11-20", "15", "50000")


def test_setup_view_without_any_plan_has_empty_defaults(conn):
    view = setup_view(conn, "2026-11-10")
    assert view["plan"] is None
    assert view["defaults"] == {"salary_day": "1", "salary": "", "savings_goal": ""}
    assert view["fixed_items"] == []


def test_setup_view_offers_the_last_plan_as_defaults(conn):
    start_cycle(conn, "2026-11-10", "5", "52000.50", "4000")
    view = setup_view(conn, "2026-12-20")  # a new month with no plan yet
    assert view["plan"] is None
    assert view["defaults"] == {"salary_day": "5", "salary": "52000.50", "savings_goal": "4000"}


def test_salary_and_savings_goal_can_be_changed_from_text(conn):
    plan_id = start_cycle(conn, "2026-11-10", "1", "50000", "5000")
    change_salary(conn, plan_id, "55000")
    change_savings_goal(conn, plan_id, "6000")
    plan = get_plan(conn, plan_id)
    assert plan["salary_paise"] == 5500000
    assert plan["savings_goal_paise"] == 600000
    change_savings_goal(conn, plan_id, "")
    assert get_plan(conn, plan_id)["savings_goal_paise"] == 0


def test_fixed_items_can_be_added_changed_and_switched_off(conn):
    rent = add_fixed(conn, " Rent ", "expense", "15000")
    add_fixed(conn, "RD", "deposit", "5000")
    change_fixed_amount(conn, rent, "16000")
    switch_fixed(conn, rent, False)
    view = setup_view(conn, "2026-11-10")
    assert [item["name"] for item in view["fixed_items"]] == ["RD", "Rent"]
    assert view["totals"] == {"expense": 0, "deposit": 500000}
    switch_fixed(conn, rent, True)
    assert setup_view(conn, "2026-11-10")["totals"]["expense"] == 1600000


def test_bad_fixed_item_input_gives_plain_errors(conn):
    with pytest.raises(ValueError):
        add_fixed(conn, "", "expense", "100")
    with pytest.raises(ValueError):
        add_fixed(conn, None, "expense", "100")
    with pytest.raises(ValueError):
        add_fixed(conn, "Rent", "expense", "abc")
    with pytest.raises(ValueError):
        add_fixed(conn, "Rent", "gift", "100")
    with pytest.raises(ValueError):
        change_fixed_amount(conn, 999, "100")
    with pytest.raises(ValueError):
        switch_fixed(conn, 999, True)
