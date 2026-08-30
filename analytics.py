"""
analytics.py — Budget calculations and chart data preparation.

All functions here are pure business-logic; no GUI dependencies.
"""

from typing import Dict, List, Tuple, Optional
from models import Expense, Budget


def spending_by_category(expenses: List[Expense]) -> Dict[str, float]:
    """
    Aggregate total spending per category from a list of expenses.

    Args:
        expenses: List of Expense objects.

    Returns:
        Dict mapping category name → total amount spent.
    """
    totals: Dict[str, float] = {}
    for exp in expenses:
        totals[exp.category] = round(totals.get(exp.category, 0.0) + exp.amount, 2)
    return totals


def total_spending(expenses: List[Expense]) -> float:
    """
    Sum all expense amounts.

    Args:
        expenses: List of Expense objects.

    Returns:
        Total amount as a rounded float.
    """
    return round(sum(e.amount for e in expenses), 2)


def budget_status(
    expenses: List[Expense],
    budgets: List[Budget],
) -> List[Dict]:
    """
    Calculate spend vs. budget for every category that has a budget set.

    Args:
        expenses: Expenses for the relevant time period (usually current month).
        budgets:  All Budget records.

    Returns:
        List of dicts, each with keys:
            category     (str)
            limit        (float)  — monthly budget limit
            spent        (float)  — total spent in the period
            remaining    (float)  — limit − spent (may be negative)
            over_budget  (bool)   — True when spent > limit
            pct_used     (float)  — percentage of budget consumed (0-100+)
    """
    spend_map = spending_by_category(expenses)
    result = []
    for b in budgets:
        spent = spend_map.get(b.category, 0.0)
        remaining = round(b.monthly_limit - spent, 2)
        pct = (spent / b.monthly_limit * 100) if b.monthly_limit > 0 else 0.0
        result.append(
            {
                "category": b.category,
                "limit": b.monthly_limit,
                "spent": round(spent, 2),
                "remaining": remaining,
                "over_budget": spent > b.monthly_limit,
                "pct_used": round(pct, 1),
            }
        )
    # Sort: over-budget categories first, then by amount spent descending
    result.sort(key=lambda x: (-int(x["over_budget"]), -x["spent"]))
    return result


def pie_chart_data(expenses: List[Expense]) -> Tuple[List[str], List[float]]:
    """
    Prepare labels and values for a pie chart of spending by category.

    Args:
        expenses: List of Expense objects.

    Returns:
        Tuple of (labels_list, amounts_list) in descending amount order.
    """
    totals = spending_by_category(expenses)
    if not totals:
        return [], []
    sorted_items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    labels = [item[0] for item in sorted_items]
    amounts = [item[1] for item in sorted_items]
    return labels, amounts


def bar_chart_data(
    expenses: List[Expense],
    budgets: List[Budget],
) -> Tuple[List[str], List[float], List[float]]:
    """
    Prepare data for a grouped bar chart: spent vs. budget per category.

    Only categories that appear in either expenses or budgets are included.

    Args:
        expenses: Expenses for the current month (or any period).
        budgets:  Budget records.

    Returns:
        Tuple of (categories, spent_amounts, budget_limits).
    """
    spend_map = spending_by_category(expenses)
    budget_map = {b.category: b.monthly_limit for b in budgets}

    # Union of all categories
    all_cats = sorted(set(list(spend_map.keys()) + list(budget_map.keys())))

    spent_vals = [spend_map.get(c, 0.0) for c in all_cats]
    limit_vals = [budget_map.get(c, 0.0) for c in all_cats]
    return all_cats, spent_vals, limit_vals


def top_spending_categories(
    expenses: List[Expense], top_n: int = 5
) -> List[Tuple[str, float]]:
    """
    Return the top N categories by total spending.

    Args:
        expenses: List of Expense objects.
        top_n:    How many top categories to return.

    Returns:
        List of (category, amount) tuples, descending by amount.
    """
    totals = spending_by_category(expenses)
    sorted_cats = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    return sorted_cats[:top_n]


def monthly_summary(
    expenses: List[Expense],
    budgets: List[Budget],
) -> Dict:
    """
    Build a high-level summary dict for the dashboard header cards.

    Args:
        expenses: Expenses for the current month.
        budgets:  All budget records.

    Returns:
        Dict with keys: total_spent, total_budget, remaining, over_budget_categories.
    """
    total_spent = total_spending(expenses)
    total_budget = round(sum(b.monthly_limit for b in budgets), 2)
    remaining = round(total_budget - total_spent, 2)

    spend_map = spending_by_category(expenses)
    over_budget_cats = [
        b.category
        for b in budgets
        if spend_map.get(b.category, 0.0) > b.monthly_limit
    ]

    return {
        "total_spent": total_spent,
        "total_budget": total_budget,
        "remaining": remaining,
        "over_budget_categories": over_budget_cats,
    }
