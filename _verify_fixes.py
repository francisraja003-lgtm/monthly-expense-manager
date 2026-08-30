"""Quick verification of the three bug fixes."""
import sys, ast
sys.path.insert(0, '.')

ok = True

# ── 1. add_expense_tab — no duplicate class ──────────────────────────
with open('gui/add_expense_tab.py', encoding='utf-8') as f:
    src = f.read()
ast.parse(src)
cls_count = src.count('class AddExpenseTab')
imp_count = src.count('import tkinter as tk')
status = "OK" if cls_count == 1 and imp_count == 1 else "FAIL"
if status == "FAIL":
    ok = False
print(f"add_expense_tab.py : {status}  (classes={cls_count}, imports={imp_count})")

# ── 2. auth.py — class-level mutable list removed ────────────────────
with open('gui/auth.py', encoding='utf-8') as f:
    auth = f.read()
ast.parse(auth)
has_class_list = (
    '    _login_hint_frames:  list = []' in auth or
    '    _signup_hint_frames: list = []' in auth
)
status2 = "FIXED" if not has_class_list else "STILL PRESENT"
if has_class_list:
    ok = False
print(f"auth.py mutable class list : {status2}")

# ── 3. auth.py — canvas item leak in resize fixed ────────────────────
# The old code called create_window inside _on_canvas_resize.
# The new code uses self._card_win_id and calls coords() instead.
has_leak = 'create_window(cw //' in auth
has_fix  = '_card_win_id' in auth and 'self._bg_canvas.coords(self._card_win_id' in auth
status3 = "FIXED" if (not has_leak and has_fix) else "STILL PRESENT"
if has_leak or not has_fix:
    ok = False
print(f"auth.py canvas item leak   : {status3}")

# ── 4. Full imports ───────────────────────────────────────────────────
from gui.add_expense_tab import AddExpenseTab
from gui.auth import AuthWindow
print("Imports                    : OK")

print()
print("ALL FIXES VERIFIED" if ok else "SOME FIXES INCOMPLETE — check output above")
