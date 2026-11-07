import sqlite3
from datetime import date, timedelta

from core.cycle import MAX_SALARY_DAY, parse_date
from core.fixed_items import (
    add_fixed_item,
    fixed_totals,
    list_fixed_items,
    set_fixed_active,
    update_fixed_amount,
)
from core.goals import add_goal, list_goals
from core.limits import daily_limit
from core.money import paise_to_plain_text, rupees_to_paise
from core.plan import (
    create_plan,
    get_plan_for_date,
    set_salary,
    set_savings_goal,
)
from core.summary import cycle_summary
from core.transactions import (
    add_credit,
    add_expense,
    category_totals,
    daily_credit_totals,
    daily_totals,
    delete_transaction,
    list_transactions,
    update_transaction,
)

def home_view(conn: sqlite3.Connection, today: str):
    """Everything the home screen shows for one day, or None if no cycle covers it."""
    try:
        plan = get_plan_for_date(conn, today)
    except ValueError:
        return None
    return {
        "plan": plan,
        "limit": daily_limit(conn, plan["id"], today),
        "summary": cycle_summary(conn, plan["id"]),
        "entries": list_transactions(conn, plan["id"], today),
    }

def add_spending_today(
    conn: sqlite3.Connection,
    today: str,
    amount_text: str,
    description: str = "",
    category: str = "",
) -> int:
    """Add spending for today from what the user typed. Raises ValueError with a plain message."""
    plan = get_plan_for_date(conn, today)
    paise = rupees_to_paise(amount_text or "")
    return add_expense(
        conn, plan["id"], today, paise, description or "", category or "uncategorised"
    )

def seed_demo_data(conn: sqlite3.Connection, today: str) -> None:
    day = date.fromisoformat(today)
    start = day.replace(day=1)
    plan_id = create_plan(
        conn, start.isoformat(), rupees_to_paise("50000"), rupees_to_paise("5000")
    )
    existing = {row["name"] for row in list_fixed_items(conn, active_only=False)}
    for name, kind, amount in [
        ("Rent", "expense", "15000"),
        ("Phone EMI", "expense", "5000"),
        ("RD", "deposit", "5000"),
    ]:
        if name not in existing:
            add_fixed_item(conn, name, kind, rupees_to_paise(amount))
    if not list_goals(conn, active_only=False):
        add_goal(conn, "Phone", rupees_to_paise("12000"), "2027-04-10")
    categories = ["food", "travel", "shopping", "food"]
    for number in range(1, day.day):  # every day before today
        paise = 40000 + (number * 7919) % 40000  # between 400.00 and 800.00
        add_expense(
            conn,
            plan_id,
            start.replace(day=number).isoformat(),
            paise,
            "demo entry",
            categories[number % len(categories)],
        )
        
def parse_salary_day(text) -> int:
    """Read the salary day from text. It must be a whole number from 1 to 28."""
    message = f"Salary day must be a whole number from 1 to {MAX_SALARY_DAY}."
    try:
        day = int(str(text).strip())
    except ValueError:
        raise ValueError(message) from None
    if not 1 <= day <= MAX_SALARY_DAY:
        raise ValueError(message)
    return day


def cycle_start_for(today: str, salary_day: int) -> str:
    """The first day of the pay cycle that contains `today`, for a salary paid on salary_day."""
    day = parse_date(today)
    if day.day >= salary_day:
        return day.replace(day=salary_day).isoformat()
    # The salary day has not come yet this month, so this cycle began last month.
    if day.month == 1:
        start = date(day.year - 1, 12, salary_day)
    else:
        start = date(day.year, day.month - 1, salary_day)
    return start.isoformat()


def start_cycle(
    conn: sqlite3.Connection,
    today: str,
    salary_day_text: str,
    salary_text: str,
    savings_goal_text: str = "",
) -> int:
    """Create the pay cycle that contains today, from what the user typed."""
    salary_day = parse_salary_day(salary_day_text)
    start = cycle_start_for(today, salary_day)
    savings = (savings_goal_text or "").strip() or "0"
    return create_plan(
        conn, start, rupees_to_paise(salary_text or ""), rupees_to_paise(savings)
    )


def setup_view(conn: sqlite3.Connection, today: str) -> dict:
    """Everything the setup screen shows."""
    try:
        plan = get_plan_for_date(conn, today)
    except ValueError:
        plan = None
    latest = conn.execute(
        "SELECT * FROM monthly_plan ORDER BY cycle_start DESC LIMIT 1"
    ).fetchone()
    defaults = {"salary_day": "1", "salary": "", "savings_goal": ""}
    if latest is not None:
        defaults = {
            "salary_day": str(parse_date(latest["cycle_start"]).day),
            "salary": paise_to_plain_text(latest["salary_paise"]),
            "savings_goal": paise_to_plain_text(latest["savings_goal_paise"]),
        }
    return {
        "plan": plan,
        "defaults": defaults,
        "fixed_items": list_fixed_items(conn, active_only=False),
        "totals": fixed_totals(conn),
    }


def change_salary(conn: sqlite3.Connection, plan_id: int, salary_text: str) -> None:
    """Correct the salary of a cycle from what the user typed."""
    set_salary(conn, plan_id, rupees_to_paise(salary_text or ""))


def change_savings_goal(conn: sqlite3.Connection, plan_id: int, goal_text: str) -> None:
    """Change the extra savings goal of a cycle from what the user typed. Blank means 0."""
    set_savings_goal(conn, plan_id, rupees_to_paise((goal_text or "").strip() or "0"))


def add_fixed(conn: sqlite3.Connection, name: str, kind: str, amount_text: str) -> int:
    """Add a fixed expense or deposit from what the user typed."""
    return add_fixed_item(conn, name or "", kind, rupees_to_paise(amount_text or ""))


def change_fixed_amount(conn: sqlite3.Connection, item_id: int, amount_text: str) -> None:
    """Change the amount of a fixed item from what the user typed."""
    update_fixed_amount(conn, item_id, rupees_to_paise(amount_text or ""))


def switch_fixed(conn: sqlite3.Connection, item_id: int, active: bool) -> None:
    """Switch a fixed item on or off."""
    set_fixed_active(conn, item_id, bool(active))
    
def build_weeks(days: list) -> list:
    """Arrange days into rows of seven, Monday first. Empty slots are None."""
    if not days:
        return []
    cells = [None] * days[0]["weekday"] + list(days)
    while len(cells) % 7 != 0:
        cells.append(None)
    return [cells[i : i + 7] for i in range(0, len(cells), 7)]


def _cycle_covering(conn: sqlite3.Connection, day: date):
    """The date as text if a cycle covers it, otherwise None."""
    try:
        get_plan_for_date(conn, day.isoformat())
    except ValueError:
        return None
    return day.isoformat()


def calendar_view(conn: sqlite3.Connection, anchor: str, today: str):
    """Everything the calendar screen shows for the cycle containing `anchor`, or None."""
    try:
        plan = get_plan_for_date(conn, anchor)
    except ValueError:
        return None
    start = parse_date(plan["cycle_start"])
    end = parse_date(plan["cycle_end"])
    spent = daily_totals(conn, plan["id"])
    credited = daily_credit_totals(conn, plan["id"])
    days = []
    for offset in range((end - start).days + 1):
        current = start + timedelta(days=offset)
        text = current.isoformat()
        days.append(
            {
                "date": text,
                "day": current.day,
                "weekday": current.weekday(),  # Monday is 0
                "spent": spent.get(text, 0),
                "credited": credited.get(text, 0),
                "is_today": text == today,
            }
        )
    return {
        "plan": plan,
        "days": days,
        "weeks": build_weeks(days),
        "categories": category_totals(conn, plan["id"]),
        "previous_anchor": _cycle_covering(conn, start - timedelta(days=1)),
        "next_anchor": _cycle_covering(conn, end + timedelta(days=1)),
    }


def day_view(conn: sqlite3.Connection, day: str) -> dict:
    """The entries of one day. Raises ValueError if no cycle covers that day."""
    plan = get_plan_for_date(conn, day)
    return {"plan": plan, "entries": list_transactions(conn, plan["id"], day)}


def add_entry_on_day(
    conn: sqlite3.Connection,
    day: str,
    kind: str,
    amount_text: str,
    description: str = "",
    category: str = "",
) -> int:
    """Add spending or extra money on any day of a cycle, from what the user typed."""
    plan = get_plan_for_date(conn, day)
    paise = rupees_to_paise(amount_text or "")
    if kind == "spending":
        return add_expense(
            conn, plan["id"], day, paise, description or "", category or "uncategorised"
        )
    if kind == "credit":
        return add_credit(conn, plan["id"], day, paise, description or "")
    raise ValueError("Kind must be 'spending' or 'credit'.")


def change_entry_amount(conn: sqlite3.Connection, txn_id: int, amount_text: str) -> None:
    """Change the amount of an entry from what the user typed."""
    update_transaction(conn, txn_id, amount_paise=rupees_to_paise(amount_text or ""))


def remove_entry(conn: sqlite3.Connection, txn_id: int) -> None:
    """Delete an entry."""
    delete_transaction(conn, txn_id)
    