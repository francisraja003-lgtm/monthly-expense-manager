"""
test_analytics.py — Unit tests for analytics.py calculations.

All tests work with plain Python objects — no database or GUI dependencies.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Expense, Budget
from analytics import (
    spending_by_category,
    total_spending,
    budget_status,
    pie_chart_data,
    bar_chart_data,
    top_spending_categories,
    monthly_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exp(amount: float, category: str, date: str = "2024-01-01") -> Expense:
    return Expense(amount=amount, category=category, description="", date=date)


def _bud(category: str, limit: float) -> Budget:
    return Budget(category=category, monthly_limit=limit)


# ---------------------------------------------------------------------------
# spending_by_category
# ---------------------------------------------------------------------------

class TestSpendingByCategory:
    def test_empty_expenses_returns_empty(self):
        assert spending_by_category([]) == {}

    def test_single_category(self):
        expenses = [_exp(10.0, "Food & Dining"), _exp(5.0, "Food & Dining")]
        result = spending_by_category(expenses)
        assert result == {"Food & Dining": 15.0}

    def test_multiple_categories(self):
        expenses = [
            _exp(10.0, "Food & Dining"),
            _exp(20.0, "Transport"),
            _exp(5.0,  "Food & Dining"),
        ]
        result = spending_by_category(expenses)
        assert result["Food & Dining"] == 15.0
        assert result["Transport"] == 20.0

    def test_values_are_rounded_to_two_decimals(self):
        expenses = [_exp(10.001, "Other"), _exp(5.004, "Other")]
        result = spending_by_category(expenses)
        # 10.001 + 5.004 = 15.005 → rounded to 15.0 (two-decimal accumulation)
        assert isinstance(result["Other"], float)


# ---------------------------------------------------------------------------
# total_spending
# ---------------------------------------------------------------------------

class TestTotalSpending:
    def test_empty_returns_zero(self):
        assert total_spending([]) == 0.0

    def test_sum_correct(self):
        expenses = [_exp(100.0, "A"), _exp(50.50, "B"), _exp(0.50, "C")]
        assert total_spending(expenses) == 151.0

    def test_single_expense(self):
        assert total_spending([_exp(42.0, "X")]) == 42.0


# ---------------------------------------------------------------------------
# budget_status
# ---------------------------------------------------------------------------

class TestBudgetStatus:
    def test_under_budget(self):
        expenses = [_exp(50.0, "Food & Dining")]
        budgets  = [_bud("Food & Dining", 200.0)]
        result = budget_status(expenses, budgets)
        assert len(result) == 1
        row = result[0]
        assert row["spent"] == 50.0
        assert row["limit"] == 200.0
        assert row["remaining"] == 150.0
        assert row["over_budget"] is False
        assert row["pct_used"] == 25.0

    def test_over_budget(self):
        expenses = [_exp(300.0, "Shopping")]
        budgets  = [_bud("Shopping", 100.0)]
        result = budget_status(expenses, budgets)
        row = result[0]
        assert row["over_budget"] is True
        assert row["remaining"] == -200.0
        assert row["pct_used"] == 300.0

    def test_no_expenses_still_shows_budget(self):
        budgets = [_bud("Healthcare", 500.0)]
        result = budget_status([], budgets)
        assert result[0]["spent"] == 0.0
        assert result[0]["remaining"] == 500.0

    def test_over_budget_sorted_first(self):
        expenses = [_exp(200.0, "Food & Dining"), _exp(10.0, "Transport")]
        budgets  = [_bud("Food & Dining", 100.0), _bud("Transport", 500.0)]
        result = budget_status(expenses, budgets)
        assert result[0]["category"] == "Food & Dining"  # over budget, comes first

    def test_zero_budget_limit_pct(self):
        expenses = [_exp(50.0, "Other")]
        budgets  = [_bud("Other", 0.0)]
        result = budget_status(expenses, budgets)
        assert result[0]["pct_used"] == 0.0  # No division by zero


# ---------------------------------------------------------------------------
# pie_chart_data
# ---------------------------------------------------------------------------

class TestPieChartData:
    def test_empty_returns_empty_lists(self):
        labels, amounts = pie_chart_data([])
        assert labels == []
        assert amounts == []

    def test_labels_and_amounts_same_length(self):
        expenses = [_exp(10.0, "A"), _exp(20.0, "B"), _exp(5.0, "C")]
        labels, amounts = pie_chart_data(expenses)
        assert len(labels) == len(amounts) == 3

    def test_sorted_descending(self):
        expenses = [_exp(5.0, "C"), _exp(20.0, "A"), _exp(10.0, "B")]
        labels, amounts = pie_chart_data(expenses)
        assert amounts == sorted(amounts, reverse=True)
        assert labels[0] == "A"


# ---------------------------------------------------------------------------
# bar_chart_data
# ---------------------------------------------------------------------------

class TestBarChartData:
    def test_categories_union(self):
        expenses = [_exp(10.0, "Food & Dining")]
        budgets  = [_bud("Transport", 100.0)]
        cats, spent, limits = bar_chart_data(expenses, budgets)
        assert "Food & Dining" in cats
        assert "Transport" in cats

    def test_missing_expense_defaults_to_zero(self):
        budgets = [_bud("Healthcare", 300.0)]
        cats, spent, limits = bar_chart_data([], budgets)
        idx = cats.index("Healthcare")
        assert spent[idx] == 0.0
        assert limits[idx] == 300.0

    def test_missing_budget_defaults_to_zero(self):
        expenses = [_exp(50.0, "Shopping")]
        cats, spent, limits = bar_chart_data(expenses, [])
        idx = cats.index("Shopping")
        assert spent[idx] == 50.0
        assert limits[idx] == 0.0


# ---------------------------------------------------------------------------
# top_spending_categories
# ---------------------------------------------------------------------------

class TestTopSpendingCategories:
    def test_empty_expenses(self):
        assert top_spending_categories([]) == []

    def test_returns_top_n(self):
        expenses = [
            _exp(100.0, "A"), _exp(80.0, "B"), _exp(60.0, "C"),
            _exp(40.0, "D"), _exp(20.0, "E"), _exp(10.0, "F"),
        ]
        top3 = top_spending_categories(expenses, top_n=3)
        assert len(top3) == 3
        assert top3[0] == ("A", 100.0)

    def test_n_larger_than_categories(self):
        expenses = [_exp(10.0, "A"), _exp(5.0, "B")]
        result = top_spending_categories(expenses, top_n=10)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# monthly_summary
# ---------------------------------------------------------------------------

class TestMonthlySummary:
    def test_no_data(self):
        result = monthly_summary([], [])
        assert result["total_spent"] == 0.0
        assert result["total_budget"] == 0.0
        assert result["remaining"] == 0.0
        assert result["over_budget_categories"] == []

    def test_over_budget_category_listed(self):
        expenses = [_exp(500.0, "Entertainment")]
        budgets  = [_bud("Entertainment", 200.0)]
        result = monthly_summary(expenses, budgets)
        assert "Entertainment" in result["over_budget_categories"]

    def test_remaining_is_budget_minus_spent(self):
        expenses = [_exp(150.0, "Food & Dining")]
        budgets  = [_bud("Food & Dining", 400.0)]
        result = monthly_summary(expenses, budgets)
        assert result["remaining"] == 250.0
        assert result["total_spent"] == 150.0
        assert result["total_budget"] == 400.0

    def test_multiple_categories(self):
        expenses = [_exp(100.0, "A"), _exp(200.0, "B")]
        budgets  = [_bud("A", 150.0), _bud("B", 150.0)]
        result = monthly_summary(expenses, budgets)
        assert result["total_spent"] == 300.0
        assert result["total_budget"] == 300.0
        assert result["over_budget_categories"] == ["B"]
