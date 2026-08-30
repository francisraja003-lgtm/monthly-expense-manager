"""
utils.py — Validation helpers and date/formatting utilities.
"""

from datetime import datetime, date
from typing import Optional, Tuple


DATE_FORMAT: str = "%Y-%m-%d"
DISPLAY_DATE_FORMAT: str = "%d %b %Y"  # e.g. 01 Jan 2024

# Maximum allowed monetary input — ₹10,00,00,000 (10 crore)
MAX_AMOUNT: float = 100_000_000.0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_amount(value: str) -> Tuple[bool, Optional[float], str]:
    """
    Validate that *value* can be parsed as a positive float within the
    allowed range (0 < amount ≤ MAX_AMOUNT).

    Returns:
        (is_valid, parsed_float_or_None, error_message)
    """
    stripped = value.strip()
    if not stripped:
        return False, None, "Amount is required."
    try:
        amount = float(stripped)
    except ValueError:
        return False, None, "Amount must be a numeric value."
    if amount <= 0:
        return False, None, "Amount must be greater than zero."
    if amount > MAX_AMOUNT:
        return False, None, (
            f"Amount cannot exceed \u20b9{MAX_AMOUNT:,.0f}  (10 crore limit)."
        )
    return True, round(amount, 2), ""


def validate_date(value: str) -> Tuple[bool, Optional[str], str]:
    """
    Validate that *value* is a parseable date in YYYY-MM-DD format.

    Returns:
        (is_valid, iso_date_string_or_None, error_message)
    """
    stripped = value.strip()
    if not stripped:
        return False, None, "Date is required."
    for fmt in (DATE_FORMAT, "%d/%m/%Y", "%m/%d/%Y"):
        try:
            parsed = datetime.strptime(stripped, fmt).date()
            return True, parsed.strftime(DATE_FORMAT), ""
        except ValueError:
            continue
    return False, None, f"Date '{stripped}' is not a recognised format (use YYYY-MM-DD)."


def validate_category(value: str) -> Tuple[bool, str]:
    """
    Validate that *value* is a non-empty category string.

    Returns:
        (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, "Category is required."
    return True, ""


def validate_budget_limit(value: str) -> Tuple[bool, Optional[float], str]:
    """
    Validate that *value* can be parsed as a non-negative float within the
    allowed range (0 ≤ limit ≤ MAX_AMOUNT).

    Returns:
        (is_valid, parsed_float_or_None, error_message)
    """
    stripped = value.strip()
    if not stripped:
        return False, None, "Budget limit is required."
    try:
        limit = float(stripped)
    except ValueError:
        return False, None, "Budget limit must be a numeric value."
    if limit < 0:
        return False, None, "Budget limit cannot be negative."
    if limit > MAX_AMOUNT:
        return False, None, (
            f"Budget limit cannot exceed \u20b9{MAX_AMOUNT:,.0f}  (10 crore limit)."
        )
    return True, round(limit, 2), ""


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_currency(amount: float) -> str:
    """Return amount formatted as a currency string, e.g. '₹1,234.56'."""
    return f"\u20b9{amount:,.2f}"


def to_display_format(iso_date: str) -> str:
    """
    Convert ISO date string (YYYY-MM-DD) to dd/mm/yyyy for display only.

    The ISO format is preserved everywhere else (DB, filters, exports).

    Examples:
        '2026-08-30' -> '30/08/2026'
    """
    try:
        return datetime.strptime(iso_date, DATE_FORMAT).strftime("%d/%m/%Y")
    except ValueError:
        return iso_date  # return as-is if unparseable


def iso_to_display(iso_date: str) -> str:
    """Convert ISO date string (YYYY-MM-DD) to a human-friendly format."""
    try:
        return datetime.strptime(iso_date, DATE_FORMAT).strftime(DISPLAY_DATE_FORMAT)
    except ValueError:
        return iso_date  # Return as-is if parsing fails


def today_iso() -> str:
    """Return today's date as an ISO string (YYYY-MM-DD)."""
    return date.today().strftime(DATE_FORMAT)


def get_current_year_month() -> Tuple[int, int]:
    """Return the current (year, month) as integers."""
    today = date.today()
    return today.year, today.month


# ---------------------------------------------------------------------------
# Tkinter input restriction helper
# ---------------------------------------------------------------------------

def apply_amount_input_limit(entry_widget) -> None:
    """
    Attach a keystroke validator to *entry_widget* that:
      - Allows only digits and a single decimal point.
      - Caps the integer part at 9 digits  (covers up to ₹99,99,99,999).
      - Caps the decimal part at 2 digits.

    This prevents users from pasting/typing numbers that would overflow
    the chart scale — the MAX_AMOUNT server-side check remains a backstop.

    Args:
        entry_widget: A tkinter Entry or ttk.Entry widget.
    """
    import re

    def _is_valid(proposed: str) -> bool:
        if proposed == "":
            return True  # allow clearing the field
        # Pattern: up to 9 integer digits, optional decimal with up to 2 places
        return bool(re.fullmatch(r"\d{0,9}(\.\d{0,2})?", proposed))

    vcmd = (entry_widget.register(_is_valid), "%P")
    entry_widget.config(validate="key", validatecommand=vcmd)
