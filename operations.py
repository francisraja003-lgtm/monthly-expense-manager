"""
operations.py — All CRUD operations for users, expenses, and budgets.

GUI code should call these functions instead of writing raw SQL.
All expense/budget operations are scoped to a user_id.
"""

import csv
import hashlib
import sqlite3
from datetime import datetime
from typing import List, Optional

from database import get_connection
from models import Expense, Budget, User


# ===========================================================================
# Auth / User operations
# ===========================================================================

def _hash_password(password: str) -> str:
    """
    Return a SHA-256 hex digest of *password*.

    In production you would use bcrypt/argon2; SHA-256 is used here to
    avoid extra dependencies while still not storing plaintext.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(username: str, password: str, display_name: str = "") -> User:
    """
    Create a new user account.

    Args:
        username:     Unique login name (case-insensitive).
        password:     Plaintext password — hashed before storage.
        display_name: Optional friendly name shown in the UI.

    Returns:
        The newly created User with its assigned id.

    Raises:
        ValueError:           If username already exists.
        sqlite3.DatabaseError: On any other DB failure.
    """
    password_hash = _hash_password(password)
    created_at = datetime.now().isoformat(sep=" ", timespec="seconds")
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, display_name, created_at) "
                "VALUES (?, ?, ?, ?)",
                (username.strip(), password_hash, display_name.strip(), created_at),
            )
            return User(
                id=cursor.lastrowid,
                username=username.strip(),
                password_hash=password_hash,
                display_name=display_name.strip(),
                created_at=created_at,
            )
    except sqlite3.IntegrityError:
        raise ValueError(f"Username '{username}' is already taken.")
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Verify credentials and return the User if they match.

    Args:
        username: Login name.
        password: Plaintext password to check.

    Returns:
        User object on success, None on failure.
    """
    password_hash = _hash_password(password)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, display_name, created_at "
            "FROM users WHERE username=? COLLATE NOCASE AND password_hash=?",
            (username.strip(), password_hash),
        ).fetchone()
        if row is None:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            display_name=row["display_name"],
            created_at=row["created_at"],
        )
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[User]:
    """
    Fetch user record by username (case-insensitive, no password check).

    Returns:
        User or None.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, display_name, created_at "
            "FROM users WHERE username=? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
        if row is None:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            display_name=row["display_name"],
            created_at=row["created_at"],
        )
    finally:
        conn.close()


# ===========================================================================
# Expense operations  (all scoped by user_id)
# ===========================================================================

def add_expense(expense: Expense) -> int:
    """
    Insert a new expense record into the database.

    Args:
        expense: An Expense dataclass instance (id should be None).

    Returns:
        The newly assigned row id.
    """
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO expenses (user_id, amount, category, description, date) "
                "VALUES (?, ?, ?, ?, ?)",
                (expense.user_id, expense.amount, expense.category,
                 expense.description, expense.date),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_all_expenses(user_id: int) -> List[Expense]:
    """
    Retrieve every expense for *user_id* ordered by date descending.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, user_id, amount, category, description, date "
            "FROM expenses WHERE user_id=? ORDER BY date DESC",
            (user_id,),
        ).fetchall()
        return [_row_to_expense(r) for r in rows]
    finally:
        conn.close()


def get_expense_by_id(expense_id: int) -> Optional[Expense]:
    """Fetch a single expense by its primary key."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, user_id, amount, category, description, date "
            "FROM expenses WHERE id=?",
            (expense_id,),
        ).fetchone()
        return _row_to_expense(row) if row else None
    finally:
        conn.close()


def update_expense(expense: Expense) -> bool:
    """Update an existing expense. Returns True if a row was changed."""
    if expense.id is None:
        return False
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE expenses SET amount=?, category=?, description=?, date=? "
                "WHERE id=? AND user_id=?",
                (expense.amount, expense.category, expense.description,
                 expense.date, expense.id, expense.user_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_expense(expense_id: int) -> bool:
    """Delete an expense by primary key. Returns True if a row was deleted."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()


def search_expenses(
    user_id: int,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
) -> List[Expense]:
    """
    Search and filter expenses for *user_id*.

    All parameters except *user_id* are optional.
    """
    conditions: List[str] = ["user_id = ?"]
    params: List = [user_id]

    if category and category.strip() and category != "All":
        conditions.append("category = ?")
        params.append(category)
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)
    if amount_min is not None:
        conditions.append("amount >= ?")
        params.append(amount_min)
    if amount_max is not None:
        conditions.append("amount <= ?")
        params.append(amount_max)

    sql = (
        "SELECT id, user_id, amount, category, description, date "
        f"FROM expenses WHERE {' AND '.join(conditions)} ORDER BY date DESC"
    )
    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_expense(r) for r in rows]
    finally:
        conn.close()


def get_expenses_for_month(user_id: int, year: int, month: int) -> List[Expense]:
    """Retrieve all expenses for *user_id* in a specific calendar month."""
    prefix = f"{year}-{month:02d}"
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, user_id, amount, category, description, date "
            "FROM expenses WHERE user_id=? AND date LIKE ? ORDER BY date DESC",
            (user_id, f"{prefix}%"),
        ).fetchall()
        return [_row_to_expense(r) for r in rows]
    finally:
        conn.close()


def export_to_csv(user_id: int, filepath: str) -> int:
    """
    Export all expenses for *user_id* to a CSV file.

    Returns:
        Number of rows written.
    """
    expenses = get_all_expenses(user_id)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Date", "Category", "Amount", "Description"])
        for e in expenses:
            writer.writerow([e.id, e.date, e.category, e.amount, e.description])
    return len(expenses)


# ===========================================================================
# Budget operations  (scoped by user_id)
# ===========================================================================

def upsert_budget(budget: Budget) -> None:
    """Insert or update the monthly budget for a category/user/month combination."""
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO budgets (user_id, category, year, month, monthly_limit) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id, category, year, month) DO UPDATE SET monthly_limit=excluded.monthly_limit",
                (budget.user_id, budget.category, budget.year, budget.month, budget.monthly_limit),
            )
    finally:
        conn.close()


def get_all_budgets(user_id: int, year: int = 0, month: int = 0) -> List[Budget]:
    """
    Retrieve budget records for *user_id*.
    If year and month are provided, filter by those specific months.
    Otherwise, return budgets for current month.
    """
    from datetime import date
    
    if year == 0 or month == 0:
        today = date.today()
        year = today.year
        month = today.month
    
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, user_id, category, year, month, monthly_limit FROM budgets "
            "WHERE user_id=? AND year=? AND month=? ORDER BY category",
            (user_id, year, month),
        ).fetchall()
        return [_row_to_budget(r) for r in rows]
    finally:
        conn.close()


def get_budget_for_category(user_id: int, category: str, year: int = 0, month: int = 0) -> Optional[Budget]:
    """Fetch the budget record for a single category/user/month."""
    from datetime import date
    
    if year == 0 or month == 0:
        today = date.today()
        year = today.year
        month = today.month
    
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, user_id, category, year, month, monthly_limit FROM budgets "
            "WHERE user_id=? AND category=? AND year=? AND month=?",
            (user_id, category, year, month),
        ).fetchone()
        return _row_to_budget(row) if row else None
    finally:
        conn.close()


def delete_budget(user_id: int, category: str, year: int = 0, month: int = 0) -> bool:
    """Remove the budget for a category/user/month. Returns True if deleted."""
    from datetime import date
    
    if year == 0 or month == 0:
        today = date.today()
        year = today.year
        month = today.month
    
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM budgets WHERE user_id=? AND category=? AND year=? AND month=?",
                (user_id, category, year, month),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


# ===========================================================================
# Private helpers
# ===========================================================================

def _row_to_expense(row: sqlite3.Row) -> Expense:
    return Expense(
        id=row["id"],
        user_id=row["user_id"],
        amount=row["amount"],
        category=row["category"],
        description=row["description"],
        date=row["date"],
    )


def _row_to_budget(row: sqlite3.Row) -> Budget:
    return Budget(
        id=row["id"],
        user_id=row["user_id"],
        category=row["category"],
        year=row["year"],
        month=row["month"],
        monthly_limit=row["monthly_limit"],
    )
