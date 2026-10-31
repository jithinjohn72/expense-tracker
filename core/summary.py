"""Cycle summary: where the money is, in clearly separate buckets."""
import sqlite3

from core.fixed_items import fixed_totals
from core.goals import total_set_asides
from core.plan import carried_in, get_plan


def _sum_transactions(conn: sqlite3.Connection, plan_id: int, direction: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_paise), 0) AS total "
        "FROM transactions WHERE plan_id = ? AND direction = ?",
        (plan_id, direction),
    ).fetchone()
    return row["total"]


def cycle_figures(conn: sqlite3.Connection, plan_id: int) -> dict:
    """Fixed expenses, deposits and goal set-asides that apply to a cycle.

    A closed cycle uses the numbers frozen when it was closed. An open cycle uses
    today's fixed items and goals.
    """
    closed = conn.execute("SELECT * FROM cycle_close WHERE plan_id = ?", (plan_id,)).fetchone()
    if closed is not None:
        return {
            "fixed_expenses": closed["fixed_expenses_paise"],
            "deposits": closed["deposits_paise"],
            "set_asides": closed["set_asides_paise"],
        }
    fixed = fixed_totals(conn)
    return {
        "fixed_expenses": fixed["expense"],
        "deposits": fixed["deposit"],
        "set_asides": total_set_asides(conn, plan_id),
    }


def cycle_summary(conn: sqlite3.Connection, plan_id: int) -> dict:
    """Return every bucket for one cycle, in paise."""
    plan = get_plan(conn, plan_id)
    figures = cycle_figures(conn, plan_id)
    extra_credits = _sum_transactions(conn, plan_id, "credit")
    spent = _sum_transactions(conn, plan_id, "debit")
    carried = carried_in(conn, plan_id)
    pool = (
        plan["salary_paise"]
        + extra_credits
        + carried
        - figures["fixed_expenses"]
        - figures["deposits"]
        - plan["savings_goal_paise"]
        - figures["set_asides"]
    )
    return {
        "salary": plan["salary_paise"],
        "extra_credits": extra_credits,
        "carried_in": carried,
        "locked_deposits": figures["deposits"],
        "fixed_expenses": figures["fixed_expenses"],
        "reserved_savings": plan["savings_goal_paise"],
        "set_asides": figures["set_asides"],
        "spendable_pool": pool,
        "spent": spent,
        "left_to_spend": pool - spent,
        "over_planned": pool < 0,
    }