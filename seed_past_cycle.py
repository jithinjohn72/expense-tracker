"""Add a finished cycle before your earliest one, so you can try the Month end screen today.

Usage (close the app first):
    python seed_past_cycle.py PATH_TO_THE_APP_DATABASE

The database file is called expense_tracker.db. The Month end screen shows the folder
that holds it (the backups folder sits inside the same folder).
"""
import sys
from datetime import date, timedelta
from pathlib import Path

from core.db import get_connection, init_db
from core.plan import get_plan_for_date
from core.service import add_entry_on_day, start_cycle


def main():
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_file():
        sys.exit("Usage: python seed_past_cycle.py PATH_TO_THE_APP_DATABASE (the file must exist)")
    conn = get_connection(sys.argv[1])
    init_db(conn)
    earliest = conn.execute(
        "SELECT cycle_start FROM monthly_plan ORDER BY cycle_start LIMIT 1"
    ).fetchone()
    if earliest is None:
        sys.exit("Start a cycle on the Setup screen first, then run this again.")
    first_day = date.fromisoformat(earliest["cycle_start"])
    day_before = (first_day - timedelta(days=1)).isoformat()
    try:
        # same salary day as your cycle, so the new cycle ends the day before yours starts
        start_cycle(conn, day_before, str(first_day.day), "50000", "3000")
    except ValueError as error:
        sys.exit(f"Could not add the past cycle: {error}")
    plan = get_plan_for_date(conn, day_before)
    add_entry_on_day(conn, plan["cycle_start"], "spending", "5000", "demo shopping", "shopping")
    print(f"Added a finished cycle: {plan['cycle_start']} to {plan['cycle_end']}.")
    print("Open the app and go to Month end.")


main()