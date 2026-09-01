"""
add_expense_tab.py — "Add Expense" tab UI.

Presents a clean, well-spaced form for entering a new expense.
Theme-reactive: re-colours plain tk.* widgets on theme toggle.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False

from models import Expense, DEFAULT_CATEGORIES
from operations import add_expense
from utils import validate_amount, validate_date, validate_category, today_iso, apply_amount_input_limit
from gui.theme import TM, FONTS

_ICON_SP = "\u2009"   # thin space between icon and label text


class AddExpenseTab(ttk.Frame):
    """
    Frame that holds the 'Add Expense' form.

    Args:
        parent:           The ttk.Notebook (or any container) this frame lives in.
        user_id:          The currently logged-in user's id.
        on_expense_added: Optional callback invoked after a successful insert.
    """

    def __init__(
        self,
        parent: ttk.Notebook,
        user_id: int,
        on_expense_added: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent, style="TFrame")
        self._user_id = user_id
        self._on_expense_added = on_expense_added
        self._tk_widgets: list[tk.Widget] = []
        self._build_ui()
        TM.register(self._apply_theme)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Lay out all widgets for the Add Expense form."""
        # Outer padding — consistent with other tabs
        outer = ttk.Frame(self, style="TFrame")
        outer.pack(fill="both", expand=True, padx=32, pady=28)

        # ---- Page header -------------------------------------------
        ttk.Label(outer, text="Add New Expense", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Fill in the details below and click Save.",
            style="Subheading.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=(16, 20))

        # ---- Card container ----------------------------------------
        self._card = tk.Frame(
            outer,
            bg=TM.c("bg_card"),
            relief="flat",
            bd=0,
            highlightbackground=TM.c("border"),
            highlightthickness=1,
        )
        # Constrain card width — looks better on wide screens
        self._card.pack(fill="x", ipadx=0, ipady=0)
        self._tk_widgets.append(self._card)

        self._inner = tk.Frame(self._card, bg=TM.c("bg_card"))
        self._inner.pack(fill="x", padx=36, pady=28)
        self._tk_widgets.append(self._inner)

        # Two columns: label (col 0, fixed) + input (col 1, expands)
        self._inner.columnconfigure(0, minsize=160)
        self._inner.columnconfigure(1, weight=1)

        row = 0

        # ---- Amount ------------------------------------------------
        self._add_label(self._inner, "Amount (\u20b9) *", row)
        self._amount_var = tk.StringVar()
        amount_entry = ttk.Entry(
            self._inner, textvariable=self._amount_var, font=FONTS["body"]
        )
        amount_entry.grid(row=row, column=1, sticky="ew", pady=8, ipady=4)
        amount_entry.focus_set()
        # Restrict keystrokes: max 9 integer digits + 2 decimal places
        apply_amount_input_limit(amount_entry)
        row += 1

        # ---- Category ----------------------------------------------
        self._add_label(self._inner, "Category *", row)
        self._category_var = tk.StringVar(value=DEFAULT_CATEGORIES[0])
        ttk.Combobox(
            self._inner,
            textvariable=self._category_var,
            values=DEFAULT_CATEGORIES,
            state="readonly",
            font=FONTS["body"],
        ).grid(row=row, column=1, sticky="ew", pady=8)
        row += 1

        # ---- Date --------------------------------------------------
        self._add_label(self._inner, "Date *", row)
        if HAS_TKCALENDAR:
            from datetime import date as _date
            today = _date.today()
            self._date_entry = DateEntry(
                self._inner,
                width=20,
                date_pattern="dd/mm/yyyy",
                state="normal",
                font=FONTS["body"],
                background=TM.c("accent"),
                foreground=TM.c("text_on_accent"),
                selectbackground=TM.c("accent"),
                selectforeground=TM.c("text_on_accent"),
                normalbackground=TM.c("bg_card"),
                normalforeground=TM.c("text_primary"),
                headersbackground=TM.c("bg_sidebar"),
                headersforeground=TM.c("text_on_accent"),
                borderwidth=1,
                maxdate=today,  # Restrict to today as maximum date
            )
            self._date_entry.set_date(today)
            self._date_entry.grid(row=row, column=1, sticky="w", pady=8)
            self._date_var: Optional[tk.StringVar] = None
        else:
            self._date_var = tk.StringVar(value=today_iso())
            self._date_entry = ttk.Entry(
                self._inner, textvariable=self._date_var, font=FONTS["body"]
            )
            self._date_entry.grid(row=row, column=1, sticky="ew", pady=8, ipady=4)
        row += 1

        # ---- Description -------------------------------------------
        self._add_label(self._inner, "Description", row)
        self._desc_var = tk.StringVar()
        ttk.Entry(self._inner, textvariable=self._desc_var, font=FONTS["body"]).grid(
            row=row, column=1, sticky="ew", pady=8, ipady=4
        )
        row += 1

        # ---- Separator + buttons -----------------------------------
        ttk.Separator(self._inner, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(18, 14)
        )
        row += 1

        self._btn_frame = tk.Frame(self._inner, bg=TM.c("bg_card"))
        self._btn_frame.grid(row=row, column=0, columnspan=2, sticky="e")
        self._tk_widgets.append(self._btn_frame)

        ttk.Button(
            self._btn_frame,
            text="  Clear Form  ",
            style="Secondary.TButton",
            command=self._clear_form,
        ).pack(side="left", padx=(0, 12))

        ttk.Button(
            self._btn_frame,
            text=f"💾{_ICON_SP} Save Expense",
            style="Accent.TButton",
            command=self._save_expense,
        ).pack(side="left")

        # ---- Status label ------------------------------------------
        self._status_var = tk.StringVar()
        self._status_label = tk.Label(
            outer,
            textvariable=self._status_var,
            bg=TM.c("bg_main"),
            font=FONTS["body"],
        )
        self._status_label.pack(anchor="w", pady=(16, 0))
        self._tk_widgets.append(self._status_label)

    def _add_label(self, parent: tk.Frame, text: str, row: int) -> tk.Label:
        """Right-aligned form label in the grid."""
        lbl = tk.Label(
            parent,
            text=text,
            bg=TM.c("bg_card"),
            fg=TM.c("text_secondary"),
            font=FONTS["body"],
            anchor="e",
        )
        lbl.grid(row=row, column=0, sticky="e", padx=(0, 18), pady=8)
        self._tk_widgets.append(lbl)
        return lbl

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _get_date_value(self) -> str:
        if HAS_TKCALENDAR:
            # Convert from dd/mm/yyyy to YYYY-MM-DD for database
            date_str = self._date_entry.get()
            try:
                from datetime import datetime
                parsed = datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                return parsed
            except (ValueError, AttributeError):
                return date_str
        return self._date_var.get() if self._date_var else ""

    def _save_expense(self) -> None:
        """Validate form and persist the new expense."""
        ok, amount, err = validate_amount(self._amount_var.get())
        if not ok:
            messagebox.showerror("Invalid Amount", err, parent=self)
            return

        ok_cat, err_cat = validate_category(self._category_var.get())
        if not ok_cat:
            messagebox.showerror("Invalid Category", err_cat, parent=self)
            return

        ok_date, iso_date, err_date = validate_date(self._get_date_value())
        if not ok_date:
            messagebox.showerror("Invalid Date", err_date, parent=self)
            return
        
        # Validate that date is not in the future
        from datetime import datetime, date as _date_type
        try:
            selected_date = datetime.strptime(iso_date, "%Y-%m-%d").date()
            today = _date_type.today()
            if selected_date > today:
                messagebox.showerror(
                    "Future Date Not Allowed",
                    f"You cannot add expenses for future dates.\n\nToday is {today.strftime('%d/%m/%Y')}.\n"
                    f"Selected date {selected_date.strftime('%d/%m/%Y')} is in the future.",
                    parent=self
                )
                return
        except ValueError:
            messagebox.showerror("Invalid Date", "Could not parse the date.", parent=self)
            return

        try:
            expense = Expense(
                amount=amount,
                category=self._category_var.get(),
                description=self._desc_var.get().strip(),
                date=iso_date,
                user_id=self._user_id,
            )
            new_id = add_expense(expense)
        except Exception as exc:
            messagebox.showerror("Database Error", f"Could not save expense:\n{exc}", parent=self)
            return

        self._status_var.set(f"✅  Expense saved successfully  (ID #{new_id})")
        self._status_label.config(fg=TM.c("success"))
        self._clear_form()

        if self._on_expense_added:
            self._on_expense_added()

    def _clear_form(self) -> None:
        """Reset all form fields to their defaults."""
        from datetime import date as _date
        self._amount_var.set("")
        self._category_var.set(DEFAULT_CATEGORIES[0])
        self._desc_var.set("")
        if HAS_TKCALENDAR:
            self._date_entry.set_date(_date.today())
        elif self._date_var:
            self._date_var.set(today_iso())

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        if not self.winfo_exists():
            TM.unregister(self._apply_theme)
            return
        bg_card = TM.c("bg_card")
        bg_main = TM.c("bg_main")
        text_s  = TM.c("text_secondary")
        border  = TM.c("border")

        self._card.configure(bg=bg_card, highlightbackground=border)
        self._inner.configure(bg=bg_card)
        self._btn_frame.configure(bg=bg_card)
        self._status_label.configure(bg=bg_main)

        for w in self._tk_widgets:
            if isinstance(w, tk.Label) and w.winfo_exists():
                parent_bg = bg_card if w.master is self._inner else bg_main
                w.configure(bg=parent_bg, fg=text_s)

