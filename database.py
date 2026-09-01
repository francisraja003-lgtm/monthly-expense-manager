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
                    monthly_limit REAL    NOT NULL CHECK(monthly_limit >= 0),
                    UNIQUE(user_id, category)
                )
                """
            )

        # ---- Schema migration: add user_id if missing (old DB) -----
        _migrate_add_user_id(conn)

    finally:
        conn.close()


def _migrate_add_user_id(conn: "sqlite3.Connection") -> None:
    """
    Add user_id column to expenses/budgets tables when upgrading from the
    pre-auth schema (v1).  Also adds the UNIQUE constraint on budgets by
    recreating the table when needed.
    Safe to call on an already-migrated database (no-op).
    """
    # Check which columns expenses already has
    exp_cols = {row[1] for row in conn.execute("PRAGMA table_info(expenses)")}
    bud_cols = {row[1] for row in conn.execute("PRAGMA table_info(budgets)")}

    with conn:
        if "user_id" not in exp_cols:
            conn.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")

        if "user_id" not in bud_cols:
            # budgets also needs a UNIQUE(user_id, category) constraint.
            # SQLite can't ADD CONSTRAINT via ALTER TABLE, so we rebuild the table.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS budgets_new (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL DEFAULT 0,
                    category      TEXT    NOT NULL,
                    monthly_limit REAL    NOT NULL CHECK(monthly_limit >= 0),
                    UNIQUE(user_id, category)
                )
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO budgets_new (id, user_id, category, monthly_limit) "
                "SELECT id, 0, category, monthly_limit FROM budgets"
            )
            conn.execute("DROP TABLE budgets")
            conn.execute("ALTER TABLE budgets_new RENAME TO budgets")
        else:
            # user_id column already exists — check if the UNIQUE constraint is present.
            # SQLite stores constraint info in sqlite_master; if the old budgets table
            # was created without UNIQUE(user_id, category) we must rebuild it.
            idx_rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='budgets' AND sql LIKE '%user_id%category%'"
            ).fetchall()
            # Also check the table CREATE sql for inline UNIQUE
            tbl_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='budgets'"
            ).fetchone()
            has_unique = bool(idx_rows) or (
                tbl_sql and "UNIQUE" in tbl_sql[0].upper()
            )
            if not has_unique:
                conn.execute(
                    """
                    CREATE TABLE budgets_new (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id       INTEGER NOT NULL DEFAULT 0,
                        category      TEXT    NOT NULL,
                        monthly_limit REAL    NOT NULL CHECK(monthly_limit >= 0),
                        UNIQUE(user_id, category)
                    )
                    """
                )
                conn.execute(
                    "INSERT OR IGNORE INTO budgets_new (id, user_id, category, monthly_limit) "
                    "SELECT id, user_id, category, monthly_limit FROM budgets"
                )
                conn.execute("DROP TABLE budgets")
                conn.execute("ALTER TABLE budgets_new RENAME TO budgets")
