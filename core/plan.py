import sqlite3
from datetime import timedelta

from core.cycle import cycle_end_for, parse_date
from core.money import check_paise

def create_plan(
    conn: sqlite3.Connection,
    cycle_start: str,
    salary_paise: int,
    savings_goal_paise: int = 0,
) -> int:
    """Create the plan for one pay cycle and return its id."""
    start = parse_date(cycle_start)
    end = cycle_end_for(start)
    check_paise(salary_paise, "Salary")
    check_paise(savings_goal_paise, "Savings goal", allow_zero=True)
    
    clash = conn.execute(
        "SELECT cycle_start FROM monthly_plan WHERE cycle_start <= ? AND cycle_end >= ?",
        (end.isoformat(), start.isoformat()),
    ).fetchone()
    if clash is not None:
        raise ValueError(
            f"This cycle overlaps the existing cycle starting {clash['cycle_start']}."
        )
    try:
        cursor = conn.execute(
            "INSERT INTO monthly_plan (cycle_start, cycle_end, salary_paise, savings_goal_paise) "
            "VALUES (?, ?, ?, ?)",
            (start.isoformat(), end.isoformat(), salary_paise, savings_goal_paise),
        )
    except sqlite3.IntegrityError:
        raise ValueError(
            f"A plan for the cycle starting {start.isoformat()} already exists."
        ) from None
    conn.commit()
    return cursor.lastrowid

def get_plan(conn: sqlite3.Connection, plan_id: int):
    """Return the plan row, or raise ValueError if there is no such plan."""
    row = conn.execute("SELECT * FROM monthly_plan WHERE id = ?", (plan_id,)).fetchone()
    if row is None:
        raise ValueError(f"No plan with id {plan_id}.")
    return row

def get_plan_for_date(conn: sqlite3.Connection, on_date: str):
    """Return the plan whose cycle contains the given date."""
    day = parse_date(on_date).isoformat()
    row = conn.execute(
        "SELECT * FROM monthly_plan WHERE cycle_start <= ? AND cycle_end >= ?",
        (day, day),
    ).fetchone()
    if row is None:
        raise ValueError(f"No plan covers {day}. Create a plan for this period first.")
    return row

def set_savings_goal(conn: sqlite3.Connection, plan_id: int, new_goal_paise: int) -> None:
    """Change the extra-savings goal of a plan (for example after extra income)."""
    check_paise(new_goal_paise, "Savings goal", allow_zero=True)
    require_open(conn, plan_id)    
    cursor = conn.execute(
        "UPDATE monthly_plan SET savings_goal_paise = ? WHERE id = ?",
        (new_goal_paise, plan_id),
    )
    if cursor.rowcount == 0:
        raise ValueError(f"No plan with id {plan_id}.")
    conn.commit()
    
def is_closed(conn: sqlite3.Connection, plan_id: int) -> bool:
    """True once a cycle has been closed."""
    row = conn.execute("SELECT 1 FROM cycle_close WHERE plan_id = ?", (plan_id,)).fetchone()
    return row is not None


def require_open(conn: sqlite3.Connection, plan_id: int) -> None:
    """Raise ValueError if the cycle is closed, because closed cycles are frozen."""
    if is_closed(conn, plan_id):
        raise ValueError("This cycle is closed and can no longer be changed.")


def carried_in(conn: sqlite3.Connection, plan_id: int) -> int:
    """Leftover money carried into this cycle from the cycle just before it (paise)."""
    plan = get_plan(conn, plan_id)
    previous_end = (parse_date(plan["cycle_start"]) - timedelta(days=1)).isoformat()
    row = conn.execute(
        "SELECT c.leftover_paise AS leftover FROM cycle_close c "
        "JOIN monthly_plan p ON p.id = c.plan_id "
        "WHERE p.cycle_end = ? AND c.leftover_action = 'carry'",
        (previous_end,),
    ).fetchone()
    return row["leftover"] if row is not None else 0