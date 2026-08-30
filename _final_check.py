"""_final_check.py — comprehensive pre-launch verification."""
import sys, ast, importlib, inspect, os
sys.path.insert(0, os.path.dirname(__file__))

ok = True

# ── 1. Syntax check every source file ────────────────────────────────
files = [
    "main.py", "database.py", "models.py", "operations.py",
    "analytics.py", "utils.py", "report_generator.py",
    "gui/__init__.py", "gui/theme.py", "gui/styles.py", "gui/auth.py",
    "gui/add_expense_tab.py", "gui/view_expenses_tab.py",
    "gui/dashboard_tab.py", "gui/settings_tab.py",
]
print("\n=== Syntax ===")
for f in files:
    try:
        with open(f, encoding="utf-8") as fh:
            ast.parse(fh.read())
        print(f"  OK  {f}")
    except SyntaxError as e:
        print(f"  FAIL {f}: {e}")
        ok = False

# ── 2. Import every module ────────────────────────────────────────────
print("\n=== Imports ===")
mods = [
    "database", "models", "operations", "analytics", "utils",
    "report_generator",
    "gui.theme", "gui.styles", "gui.auth",
    "gui.add_expense_tab", "gui.view_expenses_tab",
    "gui.dashboard_tab", "gui.settings_tab",
]
for m in mods:
    try:
        importlib.import_module(m)
        print(f"  OK  {m}")
    except Exception as e:
        print(f"  FAIL {m}: {e}")
        ok = False

# ── 3. Icon-spacing constant in every tab ────────────────────────────
print("\n=== Icon spacing (\u2009 thin space) ===")
tabs = [
    "gui.add_expense_tab", "gui.view_expenses_tab",
    "gui.dashboard_tab",   "gui.settings_tab",
]
for mod_name in tabs:
    mod = importlib.import_module(mod_name)
    src = inspect.getsource(mod)
    present = "_ICON_SP" in src or "\u2009" in src
    status = "OK" if present else "MISSING"
    print(f"  {status}  {mod_name}")
    if not present:
        ok = False

# ── 4. Currency symbol ────────────────────────────────────────────────
print("\n=== Currency symbol ===")
from utils import format_currency
result = format_currency(1234.56)
sym_ok = result.startswith("\u20b9")
print(f"  {'OK' if sym_ok else 'FAIL'}  format_currency(1234.56) = {result}")
if not sym_ok:
    ok = False

# ── 5. DB + operations ────────────────────────────────────────────────
print("\n=== Database & operations ===")
from database import initialize_db
from operations import (
    create_user, authenticate_user, get_user_by_username,
    add_expense, get_all_expenses, delete_expense,
    upsert_budget, get_all_budgets, delete_budget,
    get_expenses_for_month, export_to_csv,
)
from models import Expense, Budget
initialize_db()
print("  OK  initialize_db")

user = get_user_by_username("_fc_user") or create_user("_fc_user", "fc_pass99", "FC User")
print(f"  OK  user id={user.id}")

eid = add_expense(Expense(amount=500.0, category="Food & Dining",
                          description="test", date="2026-08-15", user_id=user.id))
print(f"  OK  add_expense id={eid}")

assert len(get_all_expenses(user.id)) > 0
print("  OK  get_all_expenses")

assert len(get_expenses_for_month(user.id, 2026, 8)) > 0
print("  OK  get_expenses_for_month")

upsert_budget(Budget(category="Food & Dining", monthly_limit=2000.0, user_id=user.id))
assert len(get_all_budgets(user.id)) > 0
print("  OK  upsert/get_all_budgets")

# ── 6. Analytics ─────────────────────────────────────────────────────
print("\n=== Analytics ===")
from analytics import monthly_summary, budget_status, pie_chart_data, bar_chart_data
expenses = get_expenses_for_month(user.id, 2026, 8)
budgets  = get_all_budgets(user.id)
s = monthly_summary(expenses, budgets)
print(f"  OK  monthly_summary total_spent={s['total_spent']}")
bs = budget_status(expenses, budgets)
print(f"  OK  budget_status rows={len(bs)}")
labels, amounts = pie_chart_data(expenses)
print(f"  OK  pie_chart_data labels={labels}")

# ── 7. Report generator ───────────────────────────────────────────────
print("\n=== PDF report_generator ===")
import tempfile
from report_generator import generate_pdf_report
with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
    tmppath = tmp.name
count = generate_pdf_report(expenses, budgets, tmppath,
                            "Final Check Report", "August 2026")
size  = os.path.getsize(tmppath)
os.unlink(tmppath)
print(f"  OK  generate_pdf_report count={count} size={size} bytes")
if size < 1000:
    print("  WARN  PDF seems very small")

# ── 8. Theme manager ─────────────────────────────────────────────────
print("\n=== ThemeManager ===")
from gui.theme import TM
assert TM.c("bg_main") == "#F0F4F8"
assert not TM.is_dark
print(f"  OK  light mode bg_main={TM.c('bg_main')}")
assert len(TM.chart_colors()) == 10
print(f"  OK  chart_colors count={len(TM.chart_colors())}")

# ── Cleanup ───────────────────────────────────────────────────────────
for e in get_all_expenses(user.id):
    delete_expense(e.id)
delete_budget(user.id, "Food & Dining")
print("\n  (test data cleaned up)")

print()
if ok:
    print("=" * 50)
    print("  ALL CHECKS PASSED — ready to run")
    print("  Command:  python main.py")
    print("=" * 50)
else:
    print("SOME CHECKS FAILED — review output above")
print()
