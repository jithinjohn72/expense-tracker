"""A guided tour of the whole backend, with no screens.

Run it from the project root in one of two ways:

    python try_it.py             uses a temporary database in memory. Nothing is saved.
    python try_it.py demo.db     saves the data in a file called demo.db, so you can
                                 open it afterwards (see show_tables.py).

The file name must start with "demo", so your real database can never be touched.
An old demo file is deleted at the start, so you can re-run as often as you like.

Tip: the output is long. To read it comfortably, save it to a text file and open that:
    python try_it.py demo.db > output.txt

Every "STEP" below prints one heading, so you can match each part of the output to
the code that produced it.
"""
import sys
import tempfile
from pathlib import Path

from core.backup import backup_database, restore_database
from core.closing import close_cycle, savings_totals
from core.db import get_connection, init_db
from core.fixed_items import add_fixed_item, fixed_totals, list_fixed_items
from core.goals import add_goal, list_goals
from core.limits import daily_limit
from core.money import paise_to_rupees_text as rupees
from core.money import rupees_to_paise
from core.plan import create_plan, get_plan_for_date, set_savings_goal
from core.summary import cycle_summary
from core.transactions import (
    add_credit,
    add_expense,
    category_totals,
    daily_totals,
    delete_transaction,
    list_transactions,
    update_transaction,
)

# ":memory:" means a temporary database that disappears at the end.
DB_FILE = sys.argv[1] if len(sys.argv) > 1 else ":memory:"
if DB_FILE != ":memory:":
    if not Path(DB_FILE).name.startswith("demo"):
        sys.exit("For safety, the database file name must start with 'demo', for example demo.db")
    Path(DB_FILE).unlink(missing_ok=True)  # start fresh: delete the old demo file if there is one


def heading(text):
    """Print a title so the output is easy to read."""
    print()
    print("=" * 64)
    print(text)
    print("=" * 64)


def show_summary(summary):
    """Print the separate money buckets of one cycle."""
    print(f"  Salary                {rupees(summary['salary']):>12}")
    print(f"  Extra credited        {rupees(summary['extra_credits']):>12}   (goes to the pool)")
    print(f"  Carried in            {rupees(summary['carried_in']):>12}   (leftover from last cycle)")
    print(f"  Locked deposits      -{rupees(summary['locked_deposits']):>12}   (never spendable)")
    print(f"  Fixed expenses       -{rupees(summary['fixed_expenses']):>12}")
    print(f"  Reserved savings     -{rupees(summary['reserved_savings']):>12}")
    print(f"  Goal set-asides      -{rupees(summary['set_asides']):>12}")
    print(f"  Spendable pool        {rupees(summary['spendable_pool']):>12}")
    print(f"  Spent so far         -{rupees(summary['spent']):>12}")
    print(f"  Left to spend         {rupees(summary['left_to_spend']):>12}")


# ---------------------------------------------------------------------------
heading("STEP 1: open a database and create the tables")
# get_connection opens the database; init_db creates the tables if they are missing.
conn = get_connection(DB_FILE)
init_db(conn)
print("Database ready.")

# ---------------------------------------------------------------------------
heading("STEP 2: create this month's plan (salary 50,000, savings goal 5,000)")
# Dates are always written as YYYY-MM-DD. Money is typed in rupees as text, and
# rupees_to_paise converts it to the whole paise that the database stores.
# The cycle end date (30 Nov) is worked out for us.
plan_id = create_plan(conn, "2026-11-01", rupees_to_paise("50000"), rupees_to_paise("5000"))

# ---------------------------------------------------------------------------
heading("STEP 3: add fixed items (paid at the start of the month, no due dates)")
# 'expense' items are things like rent and EMIs. 'deposit' items go to the bank
# (RD, FD) and are locked: they are kept apart and are never spendable.
add_fixed_item(conn, "Rent", "expense", rupees_to_paise("15000"))
add_fixed_item(conn, "Phone EMI", "expense", rupees_to_paise("5000"))
add_fixed_item(conn, "RD", "deposit", rupees_to_paise("5000"))
totals = fixed_totals(conn)
print(f"Fixed expenses: {rupees(totals['expense'])}")
print(f"Locked deposits: {rupees(totals['deposit'])}")

# ---------------------------------------------------------------------------
heading("STEP 4: add a purchase goal (a 12,000 phone by 10 April 2027)")
# The app works out how much to reserve in every cycle so the phone is paid for
# by the target date. That reserved amount lowers the spendable pool.
add_goal(conn, "Phone", rupees_to_paise("12000"), "2027-04-10")
for goal in list_goals(conn):
    print(f"Goal: {goal['name']}, price {rupees(goal['price_paise'])}, by {goal['target_date']}")

# ---------------------------------------------------------------------------
heading("STEP 5: five days of spending, with the daily limit each morning")
# Each day we ask for the limit FIRST, then record what was spent.
# Unspent money rolls into tomorrow's limit, and overspending lowers it.
days = [
    ("2026-11-01", "400", "lunch", "food"),
    ("2026-11-02", "900", "new shirt", "clothes"),
    ("2026-11-03", "0", "", ""),
    ("2026-11-04", "650", "bus pass", "travel"),
    ("2026-11-05", "617", "groceries", "food"),
]
for day, amount, note, category in days:
    result = daily_limit(conn, plan_id, day)
    print(f"{day}  limit {rupees(result['limit']):>9}   days left {result['days_left']}")
    if amount != "0":  # a day with no spending is simply not recorded
        add_expense(conn, plan_id, day, rupees_to_paise(amount), note, category)

# ---------------------------------------------------------------------------
heading("STEP 6: extra money arrives mid-month (3,000 freelance work on 11 Nov)")
# Extra money goes straight to the spendable pool. Days before it do not change,
# and the limit rises from the day it arrives.
print("Limit on 10 Nov, before the extra money:", rupees(daily_limit(conn, plan_id, "2026-11-10")["limit"]))
add_credit(conn, plan_id, "2026-11-11", rupees_to_paise("3000"), "freelance work")
print("Limit on 11 Nov, after the extra money: ", rupees(daily_limit(conn, plan_id, "2026-11-11")["limit"]))

# ---------------------------------------------------------------------------
heading("STEP 7: fix a mistake (edit and delete an entry)")
# Imagine we typed 5,000 instead of 500 for a coffee. update_transaction changes
# only the values we pass in. delete_transaction removes the entry completely.
mistake = add_expense(conn, plan_id, "2026-11-06", rupees_to_paise("5000"), "coffee", "food")
print("Typed by mistake:", rupees(rupees_to_paise("5000")))
update_transaction(conn, mistake, amount_paise=rupees_to_paise("500"))
print("Corrected to:    ", rupees(rupees_to_paise("500")))
delete_transaction(conn, mistake)
print("Then deleted, so the totals below are exactly as before.")

# ---------------------------------------------------------------------------
heading("STEP 8: the summary, with every bucket kept separate")
show_summary(cycle_summary(conn, plan_id))

# ---------------------------------------------------------------------------
heading("STEP 9: the data a calendar screen will need")
# The screen only knows today's date. get_plan_for_date finds the right cycle.
plan = get_plan_for_date(conn, "2026-11-17")
print(f"2026-11-17 belongs to the cycle {plan['cycle_start']} to {plan['cycle_end']}")
print("Spent per day:")
for day, total in daily_totals(conn, plan_id).items():
    print(f"  {day}: {rupees(total)}")
print("Spent per category (biggest first):")
for category, total in category_totals(conn, plan_id).items():
    print(f"  {category}: {rupees(total)}")
print("Entries on 2026-11-02 (what a tap on that day would show):")
for entry in list_transactions(conn, plan_id, "2026-11-02"):
    print(f"  {rupees(entry['amount_paise'])}  {entry['category']}  {entry['description']}")

# ---------------------------------------------------------------------------
heading("STEP 10: save part of the extra money by raising the savings goal")
# The pool drops by 1,000, so the daily limits fall a little.
set_savings_goal(conn, plan_id, rupees_to_paise("6000"))
print("Left to spend now:", rupees(cycle_summary(conn, plan_id)["left_to_spend"]))

# ---------------------------------------------------------------------------
heading("STEP 11: close the cycle on 1 Dec and carry the leftover forward")
# A cycle can only be closed after its last day. Closing freezes its numbers,
# adds this cycle's set-aside to the goal, and decides where the leftover goes:
# "savings" (into your savings) or "carry" (into the next cycle's pool).
result = close_cycle(conn, plan_id, "2026-12-01", "carry")
print(f"Leftover: {rupees(result['leftover'])}  action: {result['action']}")
print("Running totals:")
for name, value in savings_totals(conn).items():
    print(f"  {name}: {rupees(value)}")

# A closed cycle is frozen. This attempt is refused with a clear message.
try:
    add_expense(conn, plan_id, "2026-11-20", rupees_to_paise("100"), "late entry", "food")
except ValueError as error:
    print("Refused:", error)

# ---------------------------------------------------------------------------
heading("STEP 12: the next cycle starts with the carried-over money")
next_id = create_plan(conn, "2026-12-01", rupees_to_paise("50000"), rupees_to_paise("5000"))
show_summary(cycle_summary(conn, next_id))
print("Phone goal saved so far:", rupees(list_goals(conn)[0]["saved_paise"]))

# ---------------------------------------------------------------------------
heading("STEP 13: back up the database and restore it somewhere else")
with tempfile.TemporaryDirectory() as folder:  # a folder that deletes itself afterwards
    backup_file = str(Path(folder) / "backup.db")
    backup_database(conn, backup_file)
    copy = get_connection(":memory:")  # a brand-new, empty database
    init_db(copy)
    restore_database(copy, backup_file)
    names = [item["name"] for item in list_fixed_items(copy)]
    print("Fixed items found in the restored copy:", ", ".join(names))
    copy.close()

# ---------------------------------------------------------------------------
heading("STEP 14: bad input is refused with a plain message")
# Every function checks its input first. Screens can show these messages directly.
for label, action in [
    ("wrong date format", lambda: add_expense(conn, next_id, "02-12-2026", 100)),
    ("negative amount", lambda: add_expense(conn, next_id, "2026-12-02", -100)),
    ("date outside the cycle", lambda: add_expense(conn, next_id, "2027-02-01", 100)),
]:
    try:
        action()
    except ValueError as error:
        print(f"{label}: {error}")

conn.close()
print()
print("Done. Every function above is what a screen will call later.")
if DB_FILE != ":memory:":
    print(f"The data is saved in {DB_FILE}. To see every table and row, run:")
    print(f"    python show_tables.py {DB_FILE}")