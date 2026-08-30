"""
view_expenses_tab.py — "View / Manage" tab UI.

Displays all expenses in a sortable Treeview with search/filter controls.
Allows editing and deleting the selected row.
Theme-reactive via ThemeManager callbacks.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Optional
from datetime import date as _date_type

try:
    from tkcalendar import DateEntry as _DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False

from models import Expense, DEFAULT_CATEGORIES
from operations import (
    get_all_expenses,
    get_expense_by_id,
    update_expense,
    delete_expense,
    search_expenses,
    export_to_csv,
)
from utils import validate_amount, validate_date, validate_category, format_currency, today_iso, to_display_format
from gui.theme import TM, FONTS

_PAD_OUTER_X  = 28
_PAD_OUTER_Y  = 22
_GAP_SECTIONS = 14
_GAP_FILTER   = 10
_ICON_SP      = "\u2009"


def _btn_text(icon: str, label: str) -> str:
    return f"{icon}{_ICON_SP} {label}"


# ── Date picker widget ─────────────────────────────────────────────────────

class _DatePicker(tk.Frame):
    """
    Thin wrapper around tkcalendar.DateEntry.

    - state="normal" keeps the dropdown arrow active so the calendar popup
      opens with full prev/next month AND year navigation on click.
      (state="readonly" disables the calendar button in some tkcalendar builds)
    - date_pattern="dd/mm/yyyy" — displayed as dd/mm/yyyy in the field.
    - .get() always returns the raw ISO string (YYYY-MM-DD) via the
      underlying DateEntry's get() method after pattern conversion.
    Falls back to a plain Entry if tkcalendar is not installed.
    """

    def __init__(self, parent: tk.Widget, **kw) -> None:
        super().__init__(parent, bg=TM.c("bg_card"), **kw)

        if HAS_TKCALENDAR:
            # state="normal" — keeps the dropdown arrow active so the calendar
            # popup opens on click with full prev/next month & year navigation.
            # (state="readonly" disables the button in some tkcalendar builds)
            self._de = _DateEntry(
                self,
                width=13,
                date_pattern="dd/mm/yyyy",
                state="normal",
                font=FONTS["body"],
                background=TM.c("accent"),
                foreground=TM.c("text_on_accent"),
                selectbackground=TM.c("accent"),
                selectforeground=TM.c("text_on_accent"),
                normalbackground=TM.c("bg_card"),
                normalforeground=TM.c("text_primary"),
                weekendbackground=TM.c("bg_input"),
                weekendforeground=TM.c("text_primary"),
                headersbackground=TM.c("bg_sidebar"),
                headersforeground=TM.c("text_on_accent"),
                borderwidth=1,
            )
            self._de.pack(side="left")
            self._fallback_var = None
        else:
            # Plain Entry fallback — user types YYYY-MM-DD
            self._fallback_var = tk.StringVar(value=today_iso())
            self._de = ttk.Entry(
                self, textvariable=self._fallback_var,
                width=13, font=FONTS["body"],
            )
            self._de.pack(side="left")

    def get(self) -> str:
        """
        Return the selected date as an ISO string YYYY-MM-DD.
        DateEntry.get() returns the date in the display pattern (dd/mm/yyyy),
        so we parse it back to ISO for filter logic.
        """
        if HAS_TKCALENDAR:
            raw = self._de.get()  # "30/08/2026"
            try:
                from datetime import datetime as _dt
                return _dt.strptime(raw, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                return raw  # return as-is if parse fails
        return self._fallback_var.get() if self._fallback_var else ""

    def set(self, iso_value: str) -> None:
        """Set the picker to *iso_value* (YYYY-MM-DD)."""
        if HAS_TKCALENDAR:
            try:
                from datetime import datetime as _dt
                d = _dt.strptime(iso_value, "%Y-%m-%d").date()
                self._de.set_date(d)
            except ValueError:
                pass
        elif self._fallback_var:
            self._fallback_var.set(iso_value)

    def apply_theme(self) -> None:
        """Re-colour the frame background on theme toggle."""
        self.configure(bg=TM.c("bg_card"))


class ViewExpensesTab(ttk.Frame):
    """
    Frame that shows the expenses table plus search/filter/edit/delete controls.

    Args:
        parent:           Container (ttk.Notebook).
        user_id:          The currently logged-in user's id.
        on_data_changed:  Callback fired after any add/edit/delete.
    """

    def __init__(
        self,
        parent: ttk.Notebook,
        user_id: int,
        on_data_changed: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent, style="TFrame")
        self._user_id         = user_id
        self._on_data_changed = on_data_changed
        self._sort_col: Optional[str]  = None
        self._sort_reverse: bool       = False
        self._all_expenses: List[Expense] = []

        self._plain_cards:  list[tk.Frame] = []
        self._plain_labels: list[tk.Label] = []

        self._build_ui()
        self.refresh()
        TM.register(self._apply_theme)

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        """Reload data from the database and repopulate the table."""
        self._all_expenses = get_all_expenses(self._user_id)
        self._populate_tree(self._all_expenses)

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        """Build the full layout for this tab."""
        # ── Outer container with breathing room ──────────────────────
        outer = ttk.Frame(self, style="TFrame")
        outer.pack(
            fill="both", expand=True,
            padx=_PAD_OUTER_X, pady=_PAD_OUTER_Y,
        )

        # ── Section 1: Page header ────────────────────────────────────
        self._build_header(outer)

        # ── Divider ──────────────────────────────────────────────────
        ttk.Separator(outer, orient="horizontal").pack(
            fill="x", pady=(_GAP_SECTIONS, _GAP_SECTIONS)
        )

        # ── Section 2: Filter panel ───────────────────────────────────
        self._build_filter_panel(outer)

        # ── Section 3: Action buttons + record count ──────────────────
        self._build_action_bar(outer)

        # ── Section 4: Treeview ───────────────────────────────────────
        self._build_tree(outer)

    # ── Header ───────────────────────────────────────────────────────────

    def _build_header(self, parent: ttk.Frame) -> None:
        """
        Top row: 'Expenses' heading on the left,
        Refresh / PDF Report / Export CSV on the right.
        """
        hdr = ttk.Frame(parent, style="TFrame")
        hdr.pack(fill="x")

        # Page title
        ttk.Label(
            hdr, text="Expenses", style="Heading.TLabel",
        ).pack(side="left")

        # Right-side buttons — packed right-to-left so order reads
        # left-to-right visually: Refresh  |  PDF Report  |  Export CSV

        # Export CSV
        ttk.Button(
            hdr,
            text=_btn_text("📤", "Export CSV"),
            style="Secondary.TButton",
            command=self._export_csv,
        ).pack(side="right", padx=(8, 0))

        # PDF Report
        ttk.Button(
            hdr,
            text=_btn_text("📄", "PDF Report"),
            style="Accent.TButton",
            command=self._export_pdf,
        ).pack(side="right", padx=(8, 0))

        # Refresh
        ttk.Button(
            hdr,
            text=_btn_text("🔄", "Refresh"),
            style="Secondary.TButton",
            command=self.refresh,
        ).pack(side="right")

    # ── Filter panel ─────────────────────────────────────────────────────

    def _build_filter_panel(self, parent: ttk.Frame) -> None:
        """Filter card with Category | From 📅 | To 📅 on row A, amounts on row B."""
        card = tk.Frame(
            parent,
            bg=TM.c("bg_card"),
            highlightbackground=TM.c("border"),
            highlightthickness=1,
        )
        card.pack(fill="x", pady=(0, _GAP_SECTIONS))
        self._filter_card = card
        self._plain_cards.append(card)

        inner = tk.Frame(card, bg=TM.c("bg_card"))
        inner.pack(fill="x", padx=16, pady=10)
        self._filter_inner = inner
        self._plain_cards.append(inner)

        # ── Row A: Category | From | To ──────────────────────────────
        row_a = tk.Frame(inner, bg=TM.c("bg_card"))
        row_a.pack(fill="x", pady=(0, 8))
        self._plain_cards.append(row_a)

        # Category
        self._filter_cat_var = tk.StringVar(value="All")
        self._mk_filter_group(
            row_a, "Category",
            ttk.Combobox(
                row_a,
                textvariable=self._filter_cat_var,
                values=["All"] + DEFAULT_CATEGORIES,
                state="readonly",
                width=18,
                font=FONTS["body"],
            ),
        )
        self._add_filter_gap(row_a)

        # From — custom _DatePicker (always opens calendar popup)
        self._mk_filter_group(row_a, "From", None)
        self._filter_from = _DatePicker(row_a)
        self._filter_from.pack(side="left")
        self._add_filter_gap(row_a)

        # To
        self._mk_filter_group(row_a, "To", None)
        self._filter_to = _DatePicker(row_a)
        self._filter_to.pack(side="left")

        # ── Row B: Min ₹ | Max ₹ | Search | Clear ────────────────────
        row_b = tk.Frame(inner, bg=TM.c("bg_card"))
        row_b.pack(fill="x")
        self._plain_cards.append(row_b)

        self._filter_min_var = tk.StringVar()
        self._mk_filter_group(
            row_b, "Min \u20b9",
            ttk.Entry(row_b, textvariable=self._filter_min_var,
                      width=11, font=FONTS["body"]),
        )
        self._add_filter_gap(row_b)

        self._filter_max_var = tk.StringVar()
        self._mk_filter_group(
            row_b, "Max \u20b9",
            ttk.Entry(row_b, textvariable=self._filter_max_var,
                      width=11, font=FONTS["body"]),
        )
        self._add_filter_gap(row_b, extra=6)

        ttk.Button(
            row_b, text=_btn_text("🔍", "Search"),
            style="Accent.TButton", command=self._apply_filter,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            row_b, text=_btn_text("✖", "Clear"),
            style="Secondary.TButton", command=self._clear_filter,
        ).pack(side="left")

    def _mk_filter_group(
        self,
        parent: tk.Frame,
        label_text: str,
        widget: Optional[tk.Widget],
    ) -> None:
        """Pack a label, then optionally pack widget beside it."""
        lbl = tk.Label(
            parent,
            text=label_text,
            bg=TM.c("bg_card"),
            fg=TM.c("text_secondary"),
            font=FONTS["small_bold"],
        )
        lbl.pack(side="left", padx=(0, 4))
        self._plain_labels.append(lbl)
        if widget is not None:
            widget.pack(side="left")

    def _add_filter_gap(self, parent: tk.Frame, extra: int = 0) -> None:
        """Fixed horizontal spacer between filter groups."""
        tk.Frame(
            parent,
            bg=TM.c("bg_card"),
            width=_GAP_FILTER + extra,
            height=1,
        ).pack(side="left")

    def _get_filter_date(self, widget: "_DatePicker") -> str:
        """Read date string from a _DatePicker widget."""
        return widget.get()

    # ── Action bar ───────────────────────────────────────────────────────

    def _build_action_bar(self, parent: ttk.Frame) -> None:
        """Edit / Delete buttons + record count badge."""
        bar = ttk.Frame(parent, style="TFrame")
        bar.pack(fill="x", pady=(0, _GAP_SECTIONS))

        ttk.Button(
            bar,
            text=_btn_text("✏️", "Edit Selected"),
            style="Accent.TButton",
            command=self._edit_selected,
        ).pack(side="left", padx=(0, 10))

        ttk.Button(
            bar,
            text=_btn_text("🗑️", "Delete Selected"),
            style="Danger.TButton",
            command=self._delete_selected,
        ).pack(side="left")

        # Record count — right side
        self._count_var = tk.StringVar(value="")
        self._count_lbl = tk.Label(
            bar,
            textvariable=self._count_var,
            bg=TM.c("bg_main"),
            fg=TM.c("text_secondary"),
            font=FONTS["small"],
        )
        self._count_lbl.pack(side="right", padx=(0, 4))
        self._plain_labels.append(self._count_lbl)

    # ── Treeview ─────────────────────────────────────────────────────────

    def _build_tree(self, parent: ttk.Frame) -> None:
        """Build the scrollable, sortable Treeview with correct column alignment."""
        tree_card = tk.Frame(
            parent,
            bg=TM.c("bg_card"),
            highlightbackground=TM.c("border"),
            highlightthickness=1,
        )
        tree_card.pack(fill="both", expand=True)
        self._tree_frame = tree_card
        self._plain_cards.append(tree_card)

        columns = ("id", "date", "category", "amount", "description")
        self._tree = ttk.Treeview(
            tree_card,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        # Column definitions: (heading label, px width, cell anchor, min px, stretch)
        col_cfg = {
            "id":          ("ID",            50,  "center", 44,   False),
            "date":        ("Date",          100, "center", 90,   False),
            "category":    ("Category",      140, "w",      110,  False),
            "amount":      ("Amount \u20b9", 110, "e",      90,   False),
            "description": ("Description",   400, "w",      150,  True),
        }
        for col, (heading, width, anchor, minw, stretch) in col_cfg.items():
            self._tree.heading(
                col,
                text=heading,
                anchor="center" if anchor == "center" else anchor,
                command=lambda c=col: self._sort_by(c),
            )
            self._tree.column(
                col,
                width=width,
                anchor=anchor,
                minwidth=minw,
                stretch=stretch,
            )

        vsb = ttk.Scrollbar(tree_card, orient="vertical",  command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_card, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_card.rowconfigure(0, weight=1)
        tree_card.columnconfigure(0, weight=1)

        self._refresh_tree_tags()
        self._tree.bind("<Double-1>", lambda _e: self._edit_selected())

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _refresh_tree_tags(self) -> None:
        """Alternating row colours for the active theme."""
        self._tree.tag_configure("odd",  background=TM.c("bg_input"))
        self._tree.tag_configure("even", background=TM.c("bg_card"))

    def _populate_tree(self, expenses: List[Expense]) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        for i, exp in enumerate(expenses):
            tag = "odd" if i % 2 else "even"
            self._tree.insert(
                "", "end",
                iid=str(exp.id),
                values=(
                    exp.id,
                    to_display_format(exp.date),     # dd/mm/yyyy display
                    exp.category,
                    f"{exp.amount:,.2f}",             # right-aligned number, no ₹ prefix
                    exp.description,
                ),
                tags=(tag,),
            )
        n = len(expenses)
        self._count_var.set(f"{n} record{'s' if n != 1 else ''}")

    def _selected_expense_id(self) -> Optional[int]:
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _sort_by(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col    = col
            self._sort_reverse = False
        key_map = {
            "id":          lambda e: e.id or 0,
            "date":        lambda e: e.date,
            "category":    lambda e: e.category.lower(),
            "amount":      lambda e: e.amount,
            "description": lambda e: e.description.lower(),
        }
        keyfn = key_map.get(col, lambda e: e.id)
        self._populate_tree(
            sorted(self._all_expenses, key=keyfn, reverse=self._sort_reverse)
        )

    # _get_filter_date removed — _DatePicker.get() handles ISO conversion directly
        return ""

    # ------------------------------------------------------------------ #
    # Event handlers  (unchanged business logic)                           #
    # ------------------------------------------------------------------ #

    def _apply_filter(self) -> None:
        """Read filter fields and run a filtered query."""
        category = self._filter_cat_var.get()

        date_from_raw = self._filter_from.get().strip()
        date_to_raw   = self._filter_to.get().strip()

        date_from: Optional[str] = None
        date_to:   Optional[str] = None

        if date_from_raw:
            ok, iso, err = validate_date(date_from_raw)
            if not ok:
                messagebox.showerror("Invalid Date", f"'From' date: {err}", parent=self)
                return
            date_from = iso

        if date_to_raw:
            ok, iso, err = validate_date(date_to_raw)
            if not ok:
                messagebox.showerror("Invalid Date", f"'To' date: {err}", parent=self)
                return
            date_to = iso

        amount_min: Optional[float] = None
        amount_max: Optional[float] = None

        if self._filter_min_var.get().strip():
            ok, val, err = validate_amount(self._filter_min_var.get())
            if not ok:
                messagebox.showerror("Invalid Amount", f"Min amount: {err}", parent=self)
                return
            amount_min = val

        if self._filter_max_var.get().strip():
            ok, val, err = validate_amount(self._filter_max_var.get())
            if not ok:
                messagebox.showerror("Invalid Amount", f"Max amount: {err}", parent=self)
                return
            amount_max = val

        try:
            results = search_expenses(
                user_id=self._user_id,
                category=category,
                date_from=date_from,
                date_to=date_to,
                amount_min=amount_min,
                amount_max=amount_max,
            )
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return

        self._all_expenses = results
        self._populate_tree(results)

    def _clear_filter(self) -> None:
        self._filter_cat_var.set("All")
        self._filter_min_var.set("")
        self._filter_max_var.set("")
        # Reset date pickers to today
        self._filter_from.set(today_iso())
        self._filter_to.set(today_iso())
        self.refresh()

    def _edit_selected(self) -> None:
        expense_id = self._selected_expense_id()
        if expense_id is None:
            messagebox.showinfo("No Selection", "Please select an expense to edit.",
                                parent=self)
            return
        expense = get_expense_by_id(expense_id)
        if expense is None:
            messagebox.showerror("Not Found", "Expense record not found.", parent=self)
            return
        EditExpenseDialog(self, expense, on_saved=self._after_data_change)

    def _delete_selected(self) -> None:
        expense_id = self._selected_expense_id()
        if expense_id is None:
            messagebox.showinfo("No Selection", "Please select an expense to delete.",
                                parent=self)
            return
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete expense #{expense_id}?  This cannot be undone.",
            parent=self,
        ):
            return
        try:
            delete_expense(expense_id)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self._after_data_change()

    def _after_data_change(self) -> None:
        self.refresh()
        if self._on_data_changed:
            self._on_data_changed()

    def _export_csv(self) -> None:
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Expenses to CSV",
            parent=self,
        )
        if not filepath:
            return
        try:
            count = export_to_csv(self._user_id, filepath)
            messagebox.showinfo(
                "Export Complete",
                f"Exported {count} records to:\n{filepath}",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc), parent=self)

    def _export_pdf(self) -> None:
        """Export the currently displayed (filtered) expenses as a PDF report."""
        from tkinter import filedialog
        from datetime import date as _date
        from operations import get_all_budgets

        if not self._all_expenses:
            messagebox.showwarning(
                "No Data",
                "There are no expenses to export.\n"
                "Try clearing the filters or adding some expenses first.",
                parent=self,
            )
            return

        default_name = f"Expense_Report_{_date.today().strftime('%Y-%m-%d')}.pdf"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialfile=default_name,
            title="Save PDF Report",
            parent=self,
        )
        if not filepath:
            return

        budgets = get_all_budgets(self._user_id)
        dates   = [e.date for e in self._all_expenses]
        period  = f"{min(dates)}  to  {max(dates)}"

        try:
            from report_generator import generate_pdf_report
            count = generate_pdf_report(
                expenses=self._all_expenses,
                budgets=budgets,
                filepath=filepath,
                report_title="Expense Report — Filtered View",
                period_label=period,
            )
            messagebox.showinfo(
                "PDF Generated",
                f"Report saved successfully!\n\n"
                f"  Records : {count}\n"
                f"  Period  : {period}\n"
                f"  File    : {filepath}",
                parent=self,
            )
        except PermissionError:
            messagebox.showerror(
                "Permission Denied",
                f"Cannot write to:\n{filepath}\n\n"
                "Make sure the file is not already open.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("PDF Generation Failed",
                                 f"An error occurred:\n\n{exc}", parent=self)

    # ------------------------------------------------------------------ #
    # Theme                                                                #
    # ------------------------------------------------------------------ #

    def _apply_theme(self) -> None:
        if not self.winfo_exists():
            TM.unregister(self._apply_theme)
            return

        bg_card = TM.c("bg_card")
        bg_main = TM.c("bg_main")
        text_s  = TM.c("text_secondary")
        border  = TM.c("border")

        for card in self._plain_cards:
            if card.winfo_exists():
                card.configure(bg=bg_card)
                try:
                    card.configure(highlightbackground=border)
                except tk.TclError:
                    pass

        for lbl in self._plain_labels:
            if lbl.winfo_exists():
                parent_bg = bg_main if lbl is self._count_lbl else bg_card
                lbl.configure(bg=parent_bg, fg=text_s)

        self._count_lbl.configure(bg=bg_main, fg=text_s)

        # Re-colour the date picker frames
        self._filter_from.apply_theme()
        self._filter_to.apply_theme()

        self._refresh_tree_tags()
        self._populate_tree(self._all_expenses)


# ============================================================================
# Edit dialog  (no changes to logic — only minor spacing)
# ============================================================================

class EditExpenseDialog(tk.Toplevel):
    """Modal dialog for editing an existing expense."""

    def __init__(
        self,
        parent: tk.Widget,
        expense: Expense,
        on_saved: Callable,
    ) -> None:
        super().__init__(parent)
        self._expense  = expense
        self._on_saved = on_saved

        self.title(f"Edit Expense  #{expense.id}")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=TM.c("bg_card"))
        self._labels: list[tk.Label] = []
        self._build_ui()
        TM.register(self._apply_theme)

        self.update_idletasks()
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{pw - self.winfo_width()//2}+{ph - self.winfo_height()//2}")

    def _build_ui(self) -> None:
        pad = {"padx": 20, "pady": 8}
        self._inner = tk.Frame(self, bg=TM.c("bg_card"))
        self._inner.pack(fill="both", padx=28, pady=24)
        self._inner.columnconfigure(1, weight=1)

        row = 0
        title_lbl = tk.Label(
            self._inner, text="Edit Expense",
            bg=TM.c("bg_card"), fg=TM.c("text_primary"), font=FONTS["heading3"],
        )
        title_lbl.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 16))
        self._labels.append(title_lbl)
        row += 1

        # Amount
        self._amount_var = tk.StringVar(value=str(self._expense.amount))
        self._lbl(row, "Amount (\u20b9) *")
        _amt_entry = ttk.Entry(self._inner, textvariable=self._amount_var)
        _amt_entry.grid(row=row, column=1, sticky="ew", **pad)
        # Cap keystrokes to 9 integer digits + 2 decimal places
        from utils import apply_amount_input_limit
        apply_amount_input_limit(_amt_entry)
        row += 1

        # Category
        self._cat_var = tk.StringVar(value=self._expense.category)
        self._lbl(row, "Category *")
        ttk.Combobox(
            self._inner, textvariable=self._cat_var,
            values=DEFAULT_CATEGORIES, state="readonly",
        ).grid(row=row, column=1, sticky="ew", **pad)
        row += 1

        # Date
        self._lbl(row, "Date *")
        if HAS_TKCALENDAR:
            self._date_entry = _DateEntry(
                self._inner, width=16,
                date_pattern="dd/mm/yyyy",
                state="normal",
                background=TM.c("accent"), foreground=TM.c("text_on_accent"),
                selectbackground=TM.c("accent"),
                normalbackground=TM.c("bg_card"),
                normalforeground=TM.c("text_primary"),
                headersbackground=TM.c("bg_sidebar"),
                headersforeground=TM.c("text_on_accent"),
            )
            from datetime import datetime
            try:
                self._date_entry.set_date(
                    datetime.strptime(self._expense.date, "%Y-%m-%d").date()
                )
            except ValueError:
                pass
            self._date_entry.grid(row=row, column=1, sticky="w", **pad)
            self._date_var = None
        else:
            self._date_var = tk.StringVar(value=self._expense.date)
            self._date_entry = ttk.Entry(self._inner, textvariable=self._date_var)
            self._date_entry.grid(row=row, column=1, sticky="ew", **pad)
        row += 1

        # Description
        self._desc_var = tk.StringVar(value=self._expense.description)
        self._lbl(row, "Description")
        ttk.Entry(self._inner, textvariable=self._desc_var).grid(
            row=row, column=1, sticky="ew", **pad)
        row += 1

        # Buttons
        self._btn_frame = tk.Frame(self._inner, bg=TM.c("bg_card"))
        self._btn_frame.grid(row=row, column=0, columnspan=2, sticky="e",
                             pady=(16, 0))
        ttk.Button(
            self._btn_frame, text="  Cancel  ",
            style="Secondary.TButton", command=self.destroy,
        ).pack(side="left", padx=(0, 10))
        ttk.Button(
            self._btn_frame,
            text=f"💾{_ICON_SP} Save Changes",
            style="Accent.TButton", command=self._save,
        ).pack(side="left")

    def _lbl(self, row: int, text: str) -> None:
        lbl = tk.Label(
            self._inner, text=text,
            bg=TM.c("bg_card"), fg=TM.c("text_secondary"),
            font=FONTS["body"], anchor="e",
        )
        lbl.grid(row=row, column=0, sticky="e", padx=(0, 12), pady=8)
        self._labels.append(lbl)

    def _get_date(self) -> str:
        if HAS_TKCALENDAR:
            # DateEntry.get() returns dd/mm/yyyy format
            # Convert to YYYY-MM-DD for validation
            date_str = self._date_entry.get()
            try:
                from datetime import datetime
                parsed = datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                return parsed
            except (ValueError, AttributeError):
                return date_str
        return self._date_var.get() if self._date_var else ""

    def _save(self) -> None:
        ok, amount, err = validate_amount(self._amount_var.get())
        if not ok:
            messagebox.showerror("Invalid Amount", err, parent=self)
            return
        ok_c, err_c = validate_category(self._cat_var.get())
        if not ok_c:
            messagebox.showerror("Invalid Category", err_c, parent=self)
            return
        ok_d, iso_date, err_d = validate_date(self._get_date())
        if not ok_d:
            messagebox.showerror("Invalid Date", err_d, parent=self)
            return
        try:
            updated = Expense(
                id=self._expense.id,
                user_id=self._expense.user_id,
                amount=amount,
                category=self._cat_var.get(),
                description=self._desc_var.get().strip(),
                date=iso_date,
            )
            success = update_expense(updated)
            if not success:
                messagebox.showerror("Save Failed", "Could not update the expense. Please try again.", parent=self)
                return
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc), parent=self)
            return
        TM.unregister(self._apply_theme)
        self.destroy()
        self._on_saved()

    def _apply_theme(self) -> None:
        if not self.winfo_exists():
            TM.unregister(self._apply_theme)
            return
        bg = TM.c("bg_card")
        self.configure(bg=bg)
        self._inner.configure(bg=bg)
        self._btn_frame.configure(bg=bg)
        for lbl in self._labels:
            if lbl.winfo_exists():
                lbl.configure(bg=bg, fg=TM.c("text_secondary"))


# ─────────────────────────────────────────────────────────────────────────────
# Helper used by auth.py
# ─────────────────────────────────────────────────────────────────────────────

def _recolor_frame(widget: tk.Widget, bg: str, text_p: str, text_s: str) -> None:
    """Recursively recolour tk.Frame / tk.Label children."""
    try:
        if isinstance(widget, tk.Frame):
            widget.configure(bg=bg)
        elif isinstance(widget, tk.Label):
            widget.configure(bg=bg, fg=text_s)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        _recolor_frame(child, bg, text_p, text_s)
