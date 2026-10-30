"""Cycle summary: where the money is, in clearly separate buckets."""
import sqlite3

from core.fixed_items import fixed_totals
from core.plan import get_plan


def _sum_transactions(conn: sqlite3.Connection, plan_id: int, direction: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_paise), 0) AS total "
        "FROM transactions WHERE plan_id = ? AND direction = ?",
        (plan_id, direction),
    ).fetchone()
    return row["total"]


def cycle_summary(conn: sqlite3.Connection, plan_id: int) -> dict:
    """Return every bucket for one cycle, in paise."""
    plan = get_plan(conn, plan_id)
    fixed = fixed_totals(conn)
    extra_credits = _sum_transactions(conn, plan_id, "credit")
    spent = _sum_transactions(conn, plan_id, "debit")
    set_asides = 0  # purchase goals arrive in a later session
    pool = (
        plan["salary_paise"]
        + extra_credits
        - fixed["expense"]
        - fixed["deposit"]
        - plan["savings_goal_paise"]
        - set_asides
    )
    return {
        "salary": plan["salary_paise"],
        "extra_credits": extra_credits,
        "locked_deposits": fixed["deposit"],
        "fixed_expenses": fixed["expense"],
        "reserved_savings": plan["savings_goal_paise"],
        "set_asides": set_asides,
        "spendable_pool": pool,
        "spent": spent,
        "left_to_spend": pool - spent,
        "over_planned": pool < 0,
    }