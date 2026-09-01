"""
settings_tab.py — Settings tab for managing monthly budgets per category.
Theme-reactive via ThemeManager callbacks.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Optional
from datetime import datetime, date as _date_type

try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False

from models import Budget, DEFAULT_CATEGORIES
from operations import get_all_budgets, upsert_budget, delete_budget
from utils import validate_budget_limit, format_currency, apply_amount_input_limit
from gui.theme import TM, FONTS

_ICON_SP = "\u2009"


class SettingsTab(ttk.Frame):
    """
    Frame that allows the user to set/update/delete monthly budget limits
    per expense category.

    Args:
        parent:          The ttk.Notebook container.
        user_id:         The currently logged-in user's id.
        on_data_changed: Callback to refresh the dashboard after budget changes.
    """

    def __init__(
        self,
        parent: ttk.Notebook,
        user_id: int,
        on_data_changed: Optional[Callable] = None,
    ) -> None:
        super().__init__(parent, style="TFrame")
        self._user_id = user_id
        self._on_data_changed = on_data_changed

        self._plain_cards:  list[tk.Frame] = []
        self._plain_labels: list[tk.Label] = []

        self._build_ui()
        self.refresh()
        TM.register(self._apply_theme)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload budget records and repopulate the table."""
        self._populate_tree(get_all_budgets(self._user_id))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, style="TFrame")
        outer.pack(fill="both", expand=True, padx=32, pady=28)
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)

        ttk.Label(outer, text="Budget Settings", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            outer,
            text="Set a monthly spending limit per category. Amounts in \u20b9.",
            style="Subheading.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 20))

        # ---- Left: form -------------------------------------------
        self._form_card = tk.Frame(
            outer, bg=TM.c("bg_card"),
            highlightbackground=TM.c("border"), highlightthickness=1,
        )
        self._form_card.grid(row=2, column=0, sticky="nsew", padx=(0, 16))
        self._plain_cards.append(self._form_card)

        form_inner = tk.Frame(self._form_card, bg=TM.c("bg_card"))
        form_inner.pack(fill="both", padx=24, pady=20)
        form_inner.columnconfigure(1, weight=1)
        self._form_inner = form_inner
        self._plain_cards.append(form_inner)

        title_lbl = tk.Label(
            form_inner, text="Set / Update Budget",
            bg=TM.c("bg_card"), fg=TM.c("text_primary"), font=FONTS["heading3"],
        )
        title_lbl.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        self._plain_labels.append(title_lbl)

        self._lbl(form_inner, "Category *", 1)
        self._cat_var = tk.StringVar(value=DEFAULT_CATEGORIES[0])
        ttk.Combobox(
            form_inner, textvariable=self._cat_var,
            values=DEFAULT_CATEGORIES, state="readonly", font=FONTS["body"],
        ).grid(row=1, column=1, sticky="ew", pady=6)

        self._lbl(form_inner, "Month *", 2)
        if HAS_TKCALENDAR:
            self._month_entry = DateEntry(
                form_inner,
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
            )
            self._month_entry.set_date(_date_type.today())
            self._month_entry.grid(row=2, column=1, sticky="w", pady=6)
            self._month_var = None
        else:
            self._month_var = tk.StringVar(value=_date_type.today().strftime("%d/%m/%Y"))
            ttk.Entry(form_inner, textvariable=self._month_var, font=FONTS["body"], state="readonly").grid(
                row=2, column=1, sticky="ew", pady=6
            )

        self._lbl(form_inner, "Monthly Limit (\u20b9) *", 3)
        self._limit_var = tk.StringVar()
        _limit_entry = ttk.Entry(form_inner, textvariable=self._limit_var, font=FONTS["body"])
        _limit_entry.grid(row=3, column=1, sticky="ew", pady=6)
        # Restrict keystrokes: max 9 integer digits + 2 decimal places
        apply_amount_input_limit(_limit_entry)

        ttk.Button(
            form_inner, text=f"💾{_ICON_SP} Save Budget", style="Accent.TButton",
            command=self._save_budget,
        ).grid(row=4, column=0, columnspan=2, sticky="e", pady=(16, 0))

        # ---- Right: table -----------------------------------------
        self._table_card = tk.Frame(
            outer, bg=TM.c("bg_card"),
            highlightbackground=TM.c("border"), highlightthickness=1,
        )
        self._table_card.grid(row=2, column=1, sticky="nsew")
        self._plain_cards.append(self._table_card)

        table_inner = tk.Frame(self._table_card, bg=TM.c("bg_card"))
        table_inner.pack(fill="both", expand=True, padx=14, pady=14)
        self._table_inner = table_inner
        self._plain_cards.append(table_inner)

        hdr_row = tk.Frame(table_inner, bg=TM.c("bg_card"))
        hdr_row.pack(fill="x", pady=(0, 8))
        self._plain_cards.append(hdr_row)

        cur_lbl = tk.Label(
            hdr_row, text="Current Budgets",
            bg=TM.c("bg_card"), fg=TM.c("text_primary"), font=FONTS["heading3"],
        )
        cur_lbl.pack(side="left")
        self._plain_labels.append(cur_lbl)

        ttk.Button(
            hdr_row, text=f"🗑️{_ICON_SP} Delete", style="Danger.TButton",
            command=self._delete_budget,
        ).pack(side="right")

        self._tree = ttk.Treeview(
            table_inner, columns=("category", "limit"), show="headings", height=12
        )
        self._tree.heading("category", text="Category")
        self._tree.heading("limit", text="Monthly Limit")
        self._tree.column("category", width=160, anchor="w")
        self._tree.column("limit", width=120, anchor="e")

        vsb = ttk.Scrollbar(table_inner, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._refresh_tree_tags()
        self._tree.bind("<Double-1>", self._prefill_from_selection)

        # Info label
        self._info_var = tk.StringVar()
        self._info_lbl = tk.Label(
            outer, textvariable=self._info_var,
            bg=TM.c("bg_main"), fg=TM.c("success"), font=FONTS["body"],
        )
        self._info_lbl.grid(row=3, column=0, columnspan=2, sticky="w", pady=(14, 0))

        self._build_quick_fill(outer)

    def _lbl(self, parent: tk.Frame, text: str, row: int) -> tk.Label:
        lbl = tk.Label(
            parent, text=text, bg=TM.c("bg_card"),
            fg=TM.c("text_secondary"), font=FONTS["body"], anchor="e",
        )
        lbl.grid(row=row, column=0, sticky="e", padx=(0, 12), pady=6)
        self._plain_labels.append(lbl)
        return lbl

    def _build_quick_fill(self, parent: ttk.Frame) -> None:
        self._quick_card = tk.Frame(
            parent, bg=TM.c("bg_card"),
            highlightbackground=TM.c("border"), highlightthickness=1,
        )
        self._quick_card.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(20, 0))
        self._plain_cards.append(self._quick_card)

        inner = tk.Frame(self._quick_card, bg=TM.c("bg_card"))
        inner.pack(fill="x", padx=24, pady=14)
        self._quick_inner = inner
        self._plain_cards.append(inner)

        qt_lbl = tk.Label(
            inner, text="Quick Set — Apply one limit to all categories",
            bg=TM.c("bg_card"), fg=TM.c("text_primary"), font=FONTS["heading3"],
        )
        qt_lbl.pack(anchor="w", pady=(0, 10))
        self._plain_labels.append(qt_lbl)

        row_f = tk.Frame(inner, bg=TM.c("bg_card"))
        row_f.pack(fill="x")
        self._quick_row = row_f
        self._plain_cards.append(row_f)

        amt_lbl = tk.Label(
            row_f, text="Amount (\u20b9):",
            bg=TM.c("bg_card"), fg=TM.c("text_secondary"), font=FONTS["body"],
        )
        amt_lbl.pack(side="left")
        self._plain_labels.append(amt_lbl)

        self._quick_var = tk.StringVar()
        _quick_entry = ttk.Entry(row_f, textvariable=self._quick_var, width=12, font=FONTS["body"])
        _quick_entry.pack(side="left", padx=8)
        # Restrict keystrokes: max 9 integer digits + 2 decimal places
        apply_amount_input_limit(_quick_entry)
        ttk.Button(
            row_f, text=f"✅{_ICON_SP} Apply to All", style="Accent.TButton",
            command=self._quick_set_all,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_tree_tags(self) -> None:
        self._tree.tag_configure("odd",  background=TM.c("bg_input"))
        self._tree.tag_configure("even", background=TM.c("bg_card"))

    def _populate_tree(self, budgets: List[Budget]) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        for i, b in enumerate(budgets):
            tag = "odd" if i % 2 else "even"
            # Use str(i) as iid — stable, no special-char issues
            self._tree.insert(
                "", "end",
                iid=str(i),
                values=(b.category, format_currency(b.monthly_limit)),
                tags=(tag,),
            )

    def _selected_category(self) -> Optional[str]:
        """Return the category string of the selected row, or None."""
        selected = self._tree.selection()
        if not selected:
            return None
        # Values are (category, formatted_limit)
        values = self._tree.item(selected[0], "values")
        return values[0] if values else None

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _save_budget(self) -> None:
        category = self._cat_var.get()
        if not category:
            messagebox.showerror("Invalid Category", "Please select a category.", parent=self)
            return
        ok, limit, err = validate_budget_limit(self._limit_var.get())
        if not ok:
            messagebox.showerror("Invalid Amount", err, parent=self)
            return
        try:
            upsert_budget(Budget(category=category, monthly_limit=limit, user_id=self._user_id))
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc), parent=self)
            return
        self._info_var.set(f"✅  Budget saved: {category} → {format_currency(limit)}/month")
        self._limit_var.set("")
        self.refresh()
        if self._on_data_changed:
            self._on_data_changed()

    def _delete_budget(self) -> None:
        category = self._selected_category()
        if not category:
            messagebox.showinfo("No Selection", "Please select a budget row to delete.", parent=self)
            return
        if not messagebox.askyesno(
            "Confirm Delete", f"Remove budget for '{category}'?", parent=self
        ):
            return
        try:
            delete_budget(self._user_id, category)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self._info_var.set(f"🗑️  Budget removed: {category}")
        self.refresh()
        if self._on_data_changed:
            self._on_data_changed()

    def _prefill_from_selection(self, _event=None) -> None:
        """Double-click on a budget row to pre-fill the form with its values."""
        selected = self._tree.selection()
        if not selected:
            return
        values = self._tree.item(selected[0], "values")
        if len(values) >= 2:
            category  = values[0]
            raw_limit = str(values[1]).replace("\u20b9", "").replace(",", "")
            self._cat_var.set(category)
            self._limit_var.set(raw_limit)

    def _quick_set_all(self) -> None:
        ok, limit, err = validate_budget_limit(self._quick_var.get())
        if not ok:
            messagebox.showerror("Invalid Amount", err, parent=self)
            return
        if not messagebox.askyesno(
            "Quick Set Budgets",
            f"Set {format_currency(limit)}/month for ALL {len(DEFAULT_CATEGORIES)} categories?",
            parent=self,
        ):
            return
        try:
            for cat in DEFAULT_CATEGORIES:
                upsert_budget(Budget(category=cat, monthly_limit=limit, user_id=self._user_id))
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc), parent=self)
            return
        self._info_var.set(
            f"✅  Applied {format_currency(limit)}/month to all {len(DEFAULT_CATEGORIES)} categories."
        )
        self._quick_var.set("")
        self.refresh()
        if self._on_data_changed:
            self._on_data_changed()

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

        for card in self._plain_cards:
            if card.winfo_exists():
                card.configure(bg=bg_card)
                try:
                    card.configure(highlightbackground=border)
                except tk.TclError:
                    pass

        for lbl in self._plain_labels:
            if lbl.winfo_exists():
                lbl.configure(bg=bg_card, fg=text_s)

        self._info_lbl.configure(bg=bg_main, fg=TM.c("success"))
        self._refresh_tree_tags()
        self.refresh()
