"""Closing a pay cycle, and the running savings totals across cycles."""
import sqlite3

from core.cycle import parse_date
from core.fixed_items import fixed_totals
from core.goals import goal_set_aside, list_goals
from core.plan import get_plan, require_open
from core.summary import cycle_summary

VALID_ACTIONS = ("savings", "carry")


def close_cycle(
    conn: sqlite3.Connection,
    plan_id: int,
    today: str,
    leftover_action: str = "savings",
) -> dict:
    """Freeze a finished cycle: save its numbers, fund the goals, and decide the leftover.

    leftover_action is "savings" (the leftover joins your savings) or "carry"
    (the leftover is added to the next cycle's pool). A negative leftover is
    taken from savings, or from the next pool, in the same way.
    """
    plan = get_plan(conn, plan_id)
    require_open(conn, plan_id)
    if leftover_action not in VALID_ACTIONS:
        raise ValueError(f"Leftover action must be one of {VALID_ACTIONS}, got {leftover_action!r}.")
    today_text = parse_date(today).isoformat()
    if today_text <= plan["cycle_end"]:
        raise ValueError(f"This cycle runs until {plan['cycle_end']}, so it cannot be closed yet.")

    summary = cycle_summary(conn, plan_id)
    leftover = summary["left_to_spend"]
    try:
        conn.execute(
            "INSERT INTO cycle_close (plan_id, closed_on, fixed_expenses_paise, deposits_paise, "
            "set_asides_paise, leftover_paise, leftover_action) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                plan_id,
                today_text,
                summary["fixed_expenses"],
                summary["locked_deposits"],
                summary["set_asides"],
                leftover,
                leftover_action,
            ),
        )
        for goal in list_goals(conn):
            funded = goal["saved_paise"] + goal_set_aside(goal, plan["cycle_start"])
            conn.execute(
                "UPDATE goals SET saved_paise = ? WHERE id = ?",
                (min(goal["price_paise"], funded), goal["id"]),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    saved = plan["savings_goal_paise"] + (leftover if leftover_action == "savings" else 0)
    return {"leftover": leftover, "action": leftover_action, "saved_this_cycle": saved}


def savings_totals(conn: sqlite3.Connection) -> dict:
    """Running totals across all cycles, in paise.

    total_saved counts closed cycles only. Deposits are always kept apart from it.
    """
    total_saved = 0
    closed = conn.execute(
        "SELECT p.savings_goal_paise AS goal, c.leftover_paise AS leftover, "
        "c.leftover_action AS action, c.deposits_paise AS deposits "
        "FROM cycle_close c JOIN monthly_plan p ON p.id = c.plan_id"
    ).fetchall()
    deposits_locked = 0
    for row in closed:
        total_saved += row["goal"]
        if row["action"] == "savings":
            total_saved += row["leftover"]
        deposits_locked += row["deposits"]
    open_cycles = conn.execute(
        "SELECT COUNT(*) AS n FROM monthly_plan WHERE id NOT IN (SELECT plan_id FROM cycle_close)"
    ).fetchone()["n"]
    deposits_locked += open_cycles * fixed_totals(conn)["deposit"]
    in_goals = conn.execute(
        "SELECT COALESCE(SUM(saved_paise), 0) AS total FROM goals WHERE active = 1"
    ).fetchone()["total"]
    return {
        "total_saved": total_saved,
        "deposits_locked": deposits_locked,
        "saved_for_goals": in_goals,
    }