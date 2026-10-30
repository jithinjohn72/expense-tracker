from datetime import date

import pytest

from core.cycle import cycle_days, cycle_end_for, parse_date


def test_parse_date_reads_iso_text():
    assert parse_date("2026-11-01") == date(2026, 11, 1)


def test_parse_date_rejects_other_formats():
    for bad in ["01-11-2026", "2026/11/01", "20261101", "2026-13-01", "abc", ""]:
        with pytest.raises(ValueError):
            parse_date(bad)


def test_parse_date_rejects_non_text():
    with pytest.raises(ValueError):
        parse_date(None)


def test_cycle_starting_on_the_first_ends_at_month_end():
    assert cycle_end_for(date(2026, 11, 1)) == date(2026, 11, 30)


def test_cycle_starting_on_the_28th_ends_on_the_27th_of_next_month():
    assert cycle_end_for(date(2026, 11, 28)) == date(2026, 12, 27)


def test_cycle_crosses_into_the_next_year():
    assert cycle_end_for(date(2026, 12, 15)) == date(2027, 1, 14)


def test_february_cycle_in_a_normal_year():
    assert cycle_end_for(date(2026, 2, 1)) == date(2026, 2, 28)


def test_february_cycle_in_a_leap_year():
    assert cycle_end_for(date(2028, 2, 1)) == date(2028, 2, 29)


def test_salary_day_above_28_is_rejected():
    with pytest.raises(ValueError):
        cycle_end_for(date(2026, 10, 29))


def test_cycle_days_counts_both_ends():
    assert cycle_days(date(2026, 11, 1), date(2026, 11, 30)) == 30
    assert cycle_days(date(2027, 1, 28), date(2027, 2, 27)) == 31

