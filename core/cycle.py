from datetime import date, timedelta

MAX_SALARY_DAY = 28


def parse_date(text: str) -> date:
    """Turn 'YYYY-MM-DD' text into a date, or raise ValueError."""
    message = f"Date must look like YYYY-MM-DD, got {text!r}."
    try:
        parsed = date.fromisoformat(text)
    except (TypeError, ValueError):
        raise ValueError(message) from None
    if parsed.isoformat() != text:
        raise ValueError(message)
    return parsed


def cycle_end_for(start: date) -> date:
    """Return the last day of the cycle that begins on `start`."""
    if start.day > MAX_SALARY_DAY:
        raise ValueError(f"Salary day must be between 1 and {MAX_SALARY_DAY}.")
    if start.month == 12:
        next_start = date(start.year + 1, 1, start.day)
    else:
        next_start = date(start.year, start.month + 1, start.day)
    return next_start - timedelta(days=1)


def cycle_days(start: date, end: date) -> int:
    """Number of days in a cycle, counting both the first and the last day."""
    return (end - start).days + 1

