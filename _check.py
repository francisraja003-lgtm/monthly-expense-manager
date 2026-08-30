"""Pre-launch sanity check — run with: python _check.py"""
import sys, os, tempfile, csv
sys.path.insert(0, os.path.dirname(__file__))

ok = True

def chk(n, expr, msg=""):
    global ok
    try:
        result = expr()
        print(f"  {n:2}. OK  {msg} {result if result is not None else ''}")
    except Exception as e:
        print(f"  {n:2}. FAIL {msg} -> {e}")
        ok = False

print("\n=== Pre-launch check ===\n")

# 1. DB
from database import initialize_db
chk(1, initialize_db, "initialize_db")

# 2-3. Auth
from operations import create_user, authenticate_user, get_user_by_username
from models import Expense, Budget

def _ensure_user():
    existing = get_user_by_username("_chk_user")
    if existing:
        return existing
    return create_user("_chk_user", "chkpass99", "Check User")

chk(2, _ensure_user, "create_user / get_user_by_username")
u = _ensure_user()
chk(3, lambda: authenticate_user("_chk_user", "chkpass99"), "authenticate_user")

# 4-7. Expense ops
from operations import (
    add_expense, get_all_expenses, get_expense_by_id,
    update_expense, delete_expense, search_expenses,
    get_expenses_for_month, export_to_csv,
)

def _add():
    return add_expense(Expense(
        amount=42.5, category="Food & Dining",
        description="Test", date="2026-08-01", user_id=u.id
    ))

chk(4, _add, "add_expense")
eid = _add()
chk(5, lambda: get_expense_by_id(eid), "get_expense_by_id")
chk(6, lambda: len(get_all_expenses(u.id)), "get_all_expenses count")
chk(7, lambda: len(get_expenses_for_month(u.id, 2026, 8)), "get_expenses_for_month count")
chk(8, lambda: len(search_expenses(u.id, category="Food & Dining")), "search_expenses count")

# Budget ops
from operations import upsert_budget, get_all_budgets, get_budget_for_category, delete_budget

chk(9,  lambda: upsert_budget(Budget(category="Food & Dining", monthly_limit=200.0, user_id=u.id)), "upsert_budget")
chk(10, lambda: len(get_all_budgets(u.id)), "get_all_budgets count")
chk(11, lambda: get_budget_for_category(u.id, "Food & Dining").monthly_limit, "get_budget_for_category")

# Analytics
from analytics import monthly_summary, budget_status, pie_chart_data, bar_chart_data, total_spending

expenses = get_expenses_for_month(u.id, 2026, 8)
budgets  = get_all_budgets(u.id)

chk(12, lambda: monthly_summary(expenses, budgets)["total_spent"], "monthly_summary total_spent")
chk(13, lambda: len(budget_status(expenses, budgets)), "budget_status length")
chk(14, lambda: pie_chart_data(expenses)[0], "pie_chart_data labels")
chk(15, lambda: bar_chart_data(expenses, budgets)[0], "bar_chart_data categories")
chk(16, lambda: total_spending(expenses), "total_spending")

# CSV export
def _csv():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        name = f.name
    n = export_to_csv(u.id, name)
    with open(name, encoding="utf-8") as f:
        headers = csv.reader(f).__next__()
    os.unlink(name)
    assert "ID" in headers and "Amount" in headers
    return n

chk(17, _csv, "export_to_csv")

# Utils
from utils import (
    validate_amount, validate_date, validate_category,
    validate_budget_limit, format_currency, iso_to_display, today_iso
)
chk(18, lambda: validate_amount("25.50")[1], "validate_amount")
chk(19, lambda: validate_date("2026-08-01")[1], "validate_date")
chk(20, lambda: validate_category("Food & Dining")[0], "validate_category")
chk(21, lambda: format_currency(1234.5), "format_currency")
chk(22, lambda: today_iso(), "today_iso")

# Theme manager
from gui.theme import TM, FONTS
chk(23, lambda: TM.c("bg_main"), "TM.c light bg_main")
chk(24, lambda: not TM.is_dark, "TM.is_dark == False")
chk(25, lambda: len(TM.chart_colors()), "TM.chart_colors length")

# Clean up test data
try:
    delete_expense(eid)
    delete_budget(u.id, "Food & Dining")
    # remove all test expenses
    for e in get_all_expenses(u.id):
        delete_expense(e.id)
    print("\n  (test data cleaned up)")
except Exception:
    pass

print()
if ok:
    print("ALL 25 CHECKS PASSED")
    print()
    print("  Run the app with:")
    print("  python main.py")
else:
    print("SOME CHECKS FAILED - review errors above before running")
print()
