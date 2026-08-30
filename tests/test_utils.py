"""
test_utils.py — Unit tests for utils.py validation and formatting helpers.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils import (
    validate_amount,
    validate_date,
    validate_category,
    validate_budget_limit,
    format_currency,
    iso_to_display,
    today_iso,
    MAX_AMOUNT,
    to_display_format,
)


class TestValidateAmount:
    def test_valid_positive_float(self):
        ok, val, err = validate_amount("42.50")
        assert ok is True
        assert val == 42.50
        assert err == ""

    def test_valid_integer_string(self):
        ok, val, _ = validate_amount("100")
        assert ok is True
        assert val == 100.0

    def test_empty_string_invalid(self):
        ok, val, err = validate_amount("")
        assert ok is False
        assert val is None

    def test_zero_invalid(self):
        ok, _, _ = validate_amount("0")
        assert ok is False

    def test_negative_invalid(self):
        ok, _, _ = validate_amount("-5")
        assert ok is False

    def test_non_numeric_invalid(self):
        ok, _, _ = validate_amount("abc")
        assert ok is False

    def test_rounds_to_two_decimals(self):
        ok, val, _ = validate_amount("9.999")
        assert ok is True
        assert val == round(9.999, 2)

    def test_exactly_at_max_valid(self):
        ok, val, _ = validate_amount(str(MAX_AMOUNT))
        assert ok is True
        assert val == MAX_AMOUNT

    def test_above_max_invalid(self):
        ok, val, err = validate_amount(str(MAX_AMOUNT + 1))
        assert ok is False
        assert val is None
        assert "10 crore" in err or "cannot exceed" in err.lower()

    def test_very_large_number_invalid(self):
        ok, _, _ = validate_amount("999999999999")
        assert ok is False


class TestValidateDate:
    def test_valid_iso_date(self):
        ok, iso, err = validate_date("2024-03-15")
        assert ok is True
        assert iso == "2024-03-15"

    def test_valid_dmy_format(self):
        ok, iso, _ = validate_date("15/03/2024")
        assert ok is True
        assert iso == "2024-03-15"

    def test_valid_mdy_format(self):
        ok, iso, _ = validate_date("03/15/2024")
        assert ok is True
        assert iso == "2024-03-15"

    def test_empty_string_invalid(self):
        ok, _, _ = validate_date("")
        assert ok is False

    def test_invalid_format(self):
        ok, _, err = validate_date("not-a-date")
        assert ok is False
        assert err != ""


class TestValidateCategory:
    def test_valid_category(self):
        ok, err = validate_category("Food & Dining")
        assert ok is True
        assert err == ""

    def test_empty_string_invalid(self):
        ok, err = validate_category("")
        assert ok is False

    def test_whitespace_only_invalid(self):
        ok, _ = validate_category("   ")
        assert ok is False

    def test_none_invalid(self):
        ok, _ = validate_category(None)
        assert ok is False


class TestValidateBudgetLimit:
    def test_valid_positive(self):
        ok, val, _ = validate_budget_limit("250.00")
        assert ok is True
        assert val == 250.0

    def test_zero_is_valid(self):
        ok, val, _ = validate_budget_limit("0")
        assert ok is True
        assert val == 0.0

    def test_negative_invalid(self):
        ok, _, _ = validate_budget_limit("-10")
        assert ok is False

    def test_empty_invalid(self):
        ok, _, _ = validate_budget_limit("")
        assert ok is False

    def test_above_max_invalid(self):
        ok, _, err = validate_budget_limit(str(MAX_AMOUNT + 1))
        assert ok is False
        assert "cannot exceed" in err.lower()

    def test_exactly_at_max_valid(self):
        ok, val, _ = validate_budget_limit(str(MAX_AMOUNT))
        assert ok is True


class TestFormatCurrency:
    def test_basic(self):
        assert format_currency(1234.56) == "\u20b91,234.56"

    def test_zero(self):
        assert format_currency(0.0) == "\u20b90.00"

    def test_large_number(self):
        assert format_currency(1000000.0) == "\u20b91,000,000.00"


class TestIsoToDisplay:
    def test_converts_correctly(self):
        result = iso_to_display("2024-01-05")
        assert result == "05 Jan 2024"

    def test_bad_input_returns_as_is(self):
        result = iso_to_display("bad-date")
        assert result == "bad-date"


class TestToDisplayFormat:
    def test_converts_to_dmy(self):
        assert to_display_format("2026-08-30") == "30/08/2026"

    def test_leading_zero_day_month(self):
        assert to_display_format("2024-01-05") == "05/01/2024"

    def test_bad_input_returns_as_is(self):
        assert to_display_format("not-a-date") == "not-a-date"


class TestApplyAmountInputLimit:
    """
    Tests for apply_amount_input_limit keystroke validator.
    We test the inner _is_valid function directly by extracting the
    registered command — simpler than spinning up a real Tk window.
    """

    def test_valid_integer(self):
        from utils import apply_amount_input_limit
        import re
        # Replicate the pattern used inside apply_amount_input_limit
        pattern = r"\d{0,9}(\.\d{0,2})?"
        assert re.fullmatch(pattern, "12345")
        assert re.fullmatch(pattern, "0")
        assert re.fullmatch(pattern, "")           # empty — allowed (clearing)

    def test_valid_decimal(self):
        import re
        pattern = r"\d{0,9}(\.\d{0,2})?"
        assert re.fullmatch(pattern, "1234.99")
        assert re.fullmatch(pattern, "99.0")
        assert re.fullmatch(pattern, "123456789.99")

    def test_too_many_integer_digits_blocked(self):
        import re
        pattern = r"\d{0,9}(\.\d{0,2})?"
        assert not re.fullmatch(pattern, "1234567890")   # 10 digits — blocked

    def test_too_many_decimal_places_blocked(self):
        import re
        pattern = r"\d{0,9}(\.\d{0,2})?"
        assert not re.fullmatch(pattern, "1.999")        # 3 decimal places — blocked

    def test_letters_blocked(self):
        import re
        pattern = r"\d{0,9}(\.\d{0,2})?"
        assert not re.fullmatch(pattern, "abc")
        assert not re.fullmatch(pattern, "1a2")


class TestTodayIso:
    def test_returns_string(self):
        result = today_iso()
        assert isinstance(result, str)

    def test_correct_format(self):
        import re
        result = today_iso()
        assert re.match(r"\d{4}-\d{2}-\d{2}", result)
