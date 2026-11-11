-- All money is stored as whole integers in paise (1 rupee = 100 paise).
-- All dates are stored as text in YYYY-MM-DD format.

CREATE TABLE IF NOT EXISTS monthly_plan (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_start        TEXT    NOT NULL UNIQUE,
    cycle_end          TEXT    NOT NULL,
    salary_paise       INTEGER NOT NULL CHECK (salary_paise > 0),
    savings_goal_paise INTEGER NOT NULL DEFAULT 0 CHECK (savings_goal_paise >= 0),
    CHECK (cycle_end > cycle_start)
);

CREATE TABLE IF NOT EXISTS fixed_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    kind         TEXT    NOT NULL CHECK (kind IN ('expense', 'deposit')),
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    active       INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id      INTEGER NOT NULL REFERENCES monthly_plan(id),
    txn_date     TEXT    NOT NULL,
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    direction    TEXT    NOT NULL CHECK (direction IN ('debit', 'credit')),
    description  TEXT    NOT NULL DEFAULT '',
    category     TEXT    NOT NULL DEFAULT 'uncategorised'
);

CREATE TABLE IF NOT EXISTS goals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    price_paise  INTEGER NOT NULL CHECK (price_paise > 0),
    saved_paise  INTEGER NOT NULL DEFAULT 0 CHECK (saved_paise >= 0),
    target_date  TEXT    NOT NULL,
    active       INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS cycle_close (
    plan_id              INTEGER PRIMARY KEY REFERENCES monthly_plan(id),
    closed_on            TEXT    NOT NULL,
    fixed_expenses_paise INTEGER NOT NULL CHECK (fixed_expenses_paise >= 0),
    deposits_paise       INTEGER NOT NULL CHECK (deposits_paise >= 0),
    set_asides_paise     INTEGER NOT NULL CHECK (set_asides_paise >= 0),
    leftover_paise       INTEGER NOT NULL,
    leftover_action      TEXT    NOT NULL CHECK (leftover_action IN ('savings', 'carry'))
);
