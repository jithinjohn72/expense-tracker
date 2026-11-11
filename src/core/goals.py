"""Purchase goals: something expensive you are saving up for."""
import sqlite3

from core.cycle import cycles_until, parse_date
from core.money import check_paise
from core.plan import get_plan


def add_goal(
    conn: sqlite3.Connection,
    name: str,
    price_paise: int,
    target_date: str,
    saved_paise: int = 0,
) -> int:
    """Add a purchase goal and return its id."""
    name = name.strip()
    if not name:
        raise ValueError("Name cannot be empty.")
    check_paise(price_paise, "Price")
    check_paise(saved_paise, "Saved amount", allow_zero=True)
    if saved_paise > price_paise:
        raise ValueError("Saved amount cannot be more than the price.")
    target = parse_date(target_date).isoformat()
    cursor = conn.execute(
        "INSERT INTO goals (name, price_paise, saved_paise, target_date) VALUES (?, ?, ?, ?)",
        (name, price_paise, saved_paise, target),
    )
    conn.commit()
    return cursor.lastrowid


def get_goal(conn: sqlite3.Connection, goal_id: int):
    """Return the goal row, or raise ValueError if there is no such goal."""
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if row is None:
        raise ValueError(f"No goal with id {goal_id}.")
    return row


def add_to_goal(conn: sqlite3.Connection, goal_id: int, amount_paise: int) -> None:
    """Record extra money saved towards a goal. The saved amount never exceeds the price."""
    check_paise(amount_paise, "Amount")
    goal = get_goal(conn, goal_id)
    new_saved = min(goal["price_paise"], goal["saved_paise"] + amount_paise)
    conn.execute("UPDATE goals SET saved_paise = ? WHERE id = ?", (new_saved, goal_id))
    conn.commit()


def set_goal_active(conn: sqlite3.Connection, goal_id: int, active: bool) -> None:
    """Switch a goal on or off without deleting it."""
    get_goal(conn, goal_id)
    conn.execute("UPDATE goals SET active = ? WHERE id = ?", (int(active), goal_id))
    conn.commit()


def list_goals(conn: sqlite3.Connection, active_only: bool = True) -> list:
    """Return goals, soonest target date first. Active ones only by default."""
    if active_only:
        sql = "SELECT * FROM goals WHERE active = 1 ORDER BY target_date, name"
    else:
        sql = "SELECT * FROM goals ORDER BY target_date, name"
    return conn.execute(sql).fetchall()


def goal_set_aside(goal, cycle_start: str) -> int:
    """How much to reserve in one cycle for one goal, in paise, rounded up."""
    remaining = goal["price_paise"] - goal["saved_paise"]
    if remaining <= 0:
        return 0
    cycles = cycles_until(parse_date(cycle_start), parse_date(goal["target_date"]))
    return (remaining + cycles - 1) // cycles


def total_set_asides(conn: sqlite3.Connection, plan_id: int) -> int:
    """Total reserved for all active goals in this cycle (P in the logic spec)."""
    plan = get_plan(conn, plan_id)
    return sum(goal_set_aside(goal, plan["cycle_start"]) for goal in list_goals(conn))
