"""
models.py — Data classes for User, Expense, and Budget entities.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class User:
    """Represents an authenticated user account."""

    username: str
    password_hash: str
    display_name: str = ""
    created_at: str = ""
    id: Optional[int] = field(default=None)


@dataclass
class Expense:
    """Represents a single expense record."""

    amount: float
    category: str
    description: str
    date: str           # stored as ISO format string: YYYY-MM-DD
    user_id: int = 0    # FK → users.id
    id: Optional[int] = field(default=None)

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if self.amount <= 0:
            raise ValueError("Amount must be a positive number.")
        if not self.category.strip():
            raise ValueError("Category cannot be empty.")
        if not self.date.strip():
            raise ValueError("Date cannot be empty.")


@dataclass
class Budget:
    """Represents a monthly budget for a specific category."""

    category: str
    monthly_limit: float
    user_id: int = 0    # FK → users.id
    id: Optional[int] = field(default=None)

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if self.monthly_limit < 0:
            raise ValueError("Budget limit cannot be negative.")
        if not self.category.strip():
            raise ValueError("Category cannot be empty.")


# Default expense categories used throughout the app
DEFAULT_CATEGORIES: list[str] = [
    "Food & Dining",
    "Transport",
    "Housing",
    "Entertainment",
    "Healthcare",
    "Shopping",
    "Education",
    "Utilities",
    "Travel",
    "Other",
]
