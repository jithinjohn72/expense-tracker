"""The daily spending limit, with unspent money rolling into later days."""
import sqlite3

from core.cycle import parse_date
from core.fixed_items import fixed_totals
from core.plan import get_plan


def daily_limit(conn: sqlite3.Connection, plan_id: int, on_date: str) -> dict:
    """Work out how much can be spent on one day of a cycle, in paise."""
    plan = get_plan(conn, plan_id)
    day = parse_date(on_date)
    day_text = day.isoformat()
    if not (plan["cycle_start"] <= day_text <= plan["cycle_end"]):
        raise ValueError(
            f"Date {day_text} is outside this cycle "
            f"({plan['cycle_start']} to {plan['cycle_end']})."
        )
    fixed = fixed_totals(conn)
    row = conn.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN direction = 'credit' AND txn_date <= ? "
        "THEN amount_paise END), 0) AS credits_to_date, "
        "COALESCE(SUM(CASE WHEN direction = 'debit' AND txn_date < ? "
        "THEN amount_paise END), 0) AS spent_before, "
        "COALESCE(SUM(CASE WHEN direction = 'debit' AND txn_date = ? "
        "THEN amount_paise END), 0) AS spent_today "
        "FROM transactions WHERE plan_id = ?",
        (day_text, day_text, day_text, plan_id),
    ).fetchone()
    pool_to_date = (
        plan["salary_paise"]
        + row["credits_to_date"]
        - fixed["expense"]
        - fixed["deposit"]
        - plan["savings_goal_paise"]
        # purchase-goal set-asides will be subtracted here in a later session
    )
    available = pool_to_date - row["spent_before"]
    days_left = (parse_date(plan["cycle_end"]) - day).days + 1
    limit = max(available, 0) // days_left
    return {
        "date": day_text,
        "limit": limit,
        "spent_today": row["spent_today"],
        "left_today": limit - row["spent_today"],
        "days_left": days_left,
        "over_budget_by": max(-available, 0),
    }