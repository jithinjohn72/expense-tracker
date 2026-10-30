import sqlite3

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


def set_savings_goal(conn: sqlite3.Connection, plan_id: int, new_goal_paise: int) -> None:
    """Change the extra-savings goal of a plan (for example after extra income)."""
    check_paise(new_goal_paise, "Savings goal", allow_zero=True)
    cursor = conn.execute(
        "UPDATE monthly_plan SET savings_goal_paise = ? WHERE id = ?",
        (new_goal_paise, plan_id),
    )
    if cursor.rowcount == 0:
        raise ValueError(f"No plan with id {plan_id}.")
    conn.commit()
    
