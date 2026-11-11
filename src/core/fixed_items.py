import sqlite3

VALID_KINDS = ("expense", "deposit")

def _check_amount(amount_paise) -> None:
    if not isinstance(amount_paise, int) or isinstance(amount_paise, bool):
        raise ValueError("Amount must be a whole number")
    if amount_paise <= 0:
        raise ValueError("Amount must be greater than zero")
    
def add_fixed_item(conn: sqlite3.Connection, name: str, kind: str, amount_paise: int):
    name = name.strip()
    if not name:
        raise ValueError("Name cannot be null")
    if not kind in VALID_KINDS:
        raise ValueError(f"Kind must be one of {VALID_KINDS}, got {kind!r}.")
    _check_amount(amount_paise)
    try:
        cursor = conn.execute(            
            "INSERT INTO fixed_items (name, kind, amount_paise) VALUES (?, ?, ?)",
            (name, kind, amount_paise),
            )
        
    except sqlite3.IntegrityError:
        raise ValueError(f"A fixed item named {name!r} already exists.") from None
    conn.commit()
    return cursor.lastrowid

def update_fixed_amount(conn: sqlite3.Connection, item_id: int, new_amount_paise: int) -> None:
    _check_amount(new_amount_paise)
    cursor = conn.execute(
        "UPDATE fixed_items SET amount_paise = ? WHERE id = ?",
        (new_amount_paise, item_id),
    )
    if cursor.rowcount == 0:
        raise ValueError(f"No fixed item with id {item_id}.")
    conn.commit()
    
def set_fixed_active(conn: sqlite3.Connection, item_id: int, active: bool) -> None:
    cursor = conn.execute(
        "UPDATE fixed_items SET active = ? WHERE id = ?",
        (int(active), item_id),
    )
    if cursor.rowcount == 0:
        raise ValueError(f"No fixed item with id {item_id}.")
    conn.commit()
    
def list_fixed_items(conn: sqlite3.Connection, active_only: bool = True) -> list:
    if active_only:
        sql = "SELECT * FROM fixed_items WHERE active = 1 ORDER BY kind, name"
    else:
        sql = "SELECT * FROM fixed_items ORDER BY kind, name"
    return conn.execute(sql).fetchall()


def fixed_totals(conn: sqlite3.Connection) -> dict:
    totals = {"expense": 0, "deposit": 0}
    rows = conn.execute(
        "SELECT kind, SUM(amount_paise) AS total "
        "FROM fixed_items WHERE active = 1 GROUP BY kind"
    ).fetchall()
    for row in rows:
        totals[row["kind"]] = row["total"]
    return totals
