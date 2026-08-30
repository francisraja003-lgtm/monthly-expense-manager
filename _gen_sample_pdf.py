"""
_gen_sample_pdf.py — Generate a sample PDF to verify alignment & pagination.
Run with:  python _gen_sample_pdf.py
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))

from models import Expense, Budget, DEFAULT_CATEGORIES
from report_generator import generate_pdf_report

rng = random.Random(42)

# ── Build 60 sample expenses spanning two months ──────────────────────────
expenses = []
for i in range(1, 61):
    month = "08" if i <= 40 else "09"
    day   = rng.randint(1, 28)
    cat   = rng.choice(DEFAULT_CATEGORIES)
    amt   = round(rng.uniform(50, 8000), 2)
    desc  = rng.choice([
        "Lunch at restaurant", "Monthly grocery run",
        "Electricity bill", "Petrol", "Movie tickets",
        "Doctor consultation", "Online course", "Bus pass",
        "Hotel stay", "", "Miscellaneous purchase",
        "A very long description that should wrap neatly inside the cell "
        "without overflowing the table column boundary at all",
    ])
    expenses.append(Expense(
        id=i, amount=amt, category=cat,
        description=desc,
        date=f"2026-{month}-{day:02d}",
        user_id=1,
    ))

# ── Build budgets for all categories ─────────────────────────────────────
budgets = [
    Budget(id=i+1, category=cat, monthly_limit=round(rng.uniform(2000, 15000), 2), user_id=1)
    for i, cat in enumerate(DEFAULT_CATEGORIES)
]
# Make one category over-budget for visual testing
budgets[0] = Budget(id=1, category=DEFAULT_CATEGORIES[0], monthly_limit=100.0, user_id=1)

out = os.path.join(os.path.dirname(__file__), "Sample_Expense_Report.pdf")
count = generate_pdf_report(
    expenses=expenses,
    budgets=budgets,
    filepath=out,
    report_title="Expense Report — August 2026",
    period_label="August 2026",
)
print(f"Generated: {out}  ({count} records)")
