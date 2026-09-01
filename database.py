"""
database.py — SQLite connection management and schema initialization.
"""

import sqlite3
from pathlib import Path
from typing import Optional

# Database file lives next to this module
DB_PATH: Path = Path(__file__).parent / "expense_manager.db"


def get_connection() -> sqlite3.Connection:
    """
    Return a new SQLite connection with row_factory set to sqlite3.Row
    so columns are accessible by name.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_db() -> None:
    """
    Create all tables (users, expenses, budgets) if they do not already exist,
    and migrate any legacy schema that pre-dates the user_id columns.
    Called once at application startup.
    """
    conn = get_connection()
    try:
        with conn:
            # ---- Users table (for login/signup) --------------------
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT    NOT NULL,
                    display_name  TEXT    DEFAULT '',
                    created_at    TEXT    NOT NULL
                )
                """
            )

            # ---- Expenses ------------------------------------------
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL DEFAULT 0,
                    amount      REAL    NOT NULL CHECK(amount > 0),
                    category    TEXT    NOT NULL,
                    description TEXT    DEFAULT '',
                    date        TEXT    NOT NULL
                )
                """
            )

            # ---- Budgets -------------------------------------------
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS budgets (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL DEFAULT 0,
                    category      TEXT    NOT NULL,
                    year          INTEGER NOT NULL,
                    month         INTEGER NOT NULL,
                    monthly_limit REAL    NOT NULL CHECK(monthly_limit >= 0),
                    UNIQUE(user_id, category, year, month)
                )
                """
            )

        # ---- Schema migration: add user_id if missing (old DB) -----
        _migrate_add_user_id(conn)

    finally:
        conn.close()


def _migrate_add_user_id(conn: "sqlite3.Connection") -> None:
    """
    Add user_id, year, and month columns to budgets table when upgrading.
    Recreate the table to add month/year tracking for per-month budgets.
    Safe to call on an already-migrated database (no-op).
    """
    # Check which columns expenses already has
    exp_cols = {row[1] for row in conn.execute("PRAGMA table_info(expenses)")}
    bud_cols = {row[1] for row in conn.execute("PRAGMA table_info(budgets)")}

    with conn:
        if "user_id" not in exp_cols:
            conn.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")

        # Rebuild budgets table if needed (add user_id, year, month if missing)
        if "user_id" not in bud_cols or "year" not in bud_cols or "month" not in bud_cols:
            # Get current date for default year/month when migrating old budgets
            from datetime import date
            today = date.today()
            current_year = today.year
            current_month = today.month

            conn.execute(
                """
                CREATE TABLE budgets_new (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL DEFAULT 0,
                    category      TEXT    NOT NULL,
                    year          INTEGER NOT NULL,
                    month         INTEGER NOT NULL,
                    monthly_limit REAL    NOT NULL CHECK(monthly_limit >= 0),
                    UNIQUE(user_id, category, year, month)
                )
                """
            )
            # Migrate old budgets to current month/year
            conn.execute(
                f"""
                INSERT OR IGNORE INTO budgets_new (user_id, category, year, month, monthly_limit)
                SELECT 
                    COALESCE(user_id, 0),
                    category,
                    {current_year},
                    {current_month},
                    monthly_limit
                FROM budgets
                """
            )
            conn.execute("DROP TABLE budgets")
            conn.execute("ALTER TABLE budgets_new RENAME TO budgets")
