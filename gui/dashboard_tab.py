"""
dashboard_tab.py — Dashboard tab with summary cards, budget alerts,
and an embedded matplotlib chart.
Theme-reactive via ThemeManager callbacks.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
import calendar
from datetime import date

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from operations import get_expenses_for_month, get_all_budgets
from analytics import monthly_summary, budget_status, pie_chart_data, bar_chart_data
from utils import format_currency, get_current_year_month
from gui.theme import TM, FONTS

_ICON_SP = "\u2009"   # thin space between icon and label text

class DashboardTab(ttk.Frame):
    """
    Dashboard showing summary cards, budget alerts, and a matplotlib chart.

    Args:
        parent:  The ttk.Notebook container.
        user_id: The currently logged-in user's id.
    """

    def __init__(self, parent: ttk.Notebook, user_id: int) -> None:
        super().__init__(parent, style="TFrame")
        self._user_id = user_id
        self._chart_type: str = "pie"
        self._year, self._month = get_current_year_month()
        self._canvas_widget: Optional[FigureCanvasTkAgg] = None
        self._alert_inner: Optional[tk.Frame] = None

        # Collected plain-tk widget refs for theme updates
        self._bg_main_widgets:  list[tk.Widget] = []
        self._bg_card_widgets:  list[tk.Widget] = []
        self._text_p_labels:    list[tk.Label]  = []
        self._text_s_labels:    list[tk.Label]  = []

        self._build_ui()
        self.refresh()
        TM.register(self._apply_theme)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload all data and redraw the dashboard."""
        expenses = get_expenses_for_month(self._user_id, self._year, self._month)
        budgets  = get_all_budgets(self._user_id)
        summary  = monthly_summary(expenses, budgets)
        statuses = budget_status(expenses, budgets)

        self._update_summary_cards(summary)
        self._update_alerts(statuses)
        self._update_budget_bars(statuses)
        self._draw_chart(expenses, budgets)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Scrollable canvas
        self._scroll_canvas = tk.Canvas(self, bg=TM.c("bg_main"), highlightthickness=0)
        self._bg_main_widgets.append(self._scroll_canvas)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self._scroll_canvas.yview)
        self._scroll_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._scroll_canvas.pack(side="left", fill="both", expand=True)

        self._scroll_frame = tk.Frame(self._scroll_canvas, bg=TM.c("bg_main"))
        self._bg_main_widgets.append(self._scroll_frame)
        self._scroll_win_id = self._scroll_canvas.create_window(
            (0, 0), window=self._scroll_frame, anchor="nw"
        )

        def _on_resize(event):
            self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))
            self._scroll_canvas.itemconfig(self._scroll_win_id, width=event.width)

        self._scroll_frame.bind("<Configure>", _on_resize)
        self._scroll_canvas.bind(
            "<Configure>",
            lambda e: self._scroll_canvas.itemconfig(self._scroll_win_id, width=e.width),
        )
        self._scroll_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        outer = self._scroll_frame
        outer.columnconfigure(0, weight=1)

        # ---- Header ------------------------------------------------
        hdr_frame = tk.Frame(outer, bg=TM.c("bg_main"))
        self._bg_main_widgets.append(hdr_frame)
        hdr_frame.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 4))

        self._dash_lbl = tk.Label(
            hdr_frame, text="Dashboard",
            bg=TM.c("bg_main"), fg=TM.c("text_primary"), font=FONTS["heading1"],
        )
        self._dash_lbl.pack(side="left")
        self._text_p_labels.append(self._dash_lbl)
        self._bg_main_widgets.append(self._dash_lbl)

        ctrl_frame = tk.Frame(hdr_frame, bg=TM.c("bg_main"))
        self._bg_main_widgets.append(ctrl_frame)
        ctrl_frame.pack(side="right")

        self._month_lbl = tk.Label(
            ctrl_frame, text="Month:",
            bg=TM.c("bg_main"), fg=TM.c("text_secondary"), font=FONTS["body"],
        )
        self._month_lbl.pack(side="left", padx=(0, 6))
        self._text_s_labels.append(self._month_lbl)
        self._bg_main_widgets.append(self._month_lbl)

        self._month_var = tk.StringVar(
            value=f"{calendar.month_name[self._month]} {self._year}"
        )
        month_options = (
            [f"{calendar.month_name[m]} {self._year}" for m in range(1, 13)]
            + [f"{calendar.month_name[m]} {self._year - 1}" for m in range(1, 13)]
        )
        ttk.Combobox(
            ctrl_frame, textvariable=self._month_var,
            values=month_options, state="readonly", width=18, font=FONTS["body"],
        ).pack(side="left", padx=(0, 8))
        self._month_var.trace_add(
            "write", lambda *_: self._on_month_change()
        )
        ttk.Button(
            ctrl_frame, text=f"🔄{_ICON_SP} Refresh",
            style="Secondary.TButton", command=self.refresh
        ).pack(side="left")

        ttk.Button(
            ctrl_frame, text=f"📄{_ICON_SP} Download PDF",
            style="Accent.TButton", command=self._download_pdf,
        ).pack(side="left", padx=(10, 0))

        # ---- Summary cards -----------------------------------------
        self._cards_frame = tk.Frame(outer, bg=TM.c("bg_main"))
        self._bg_main_widgets.append(self._cards_frame)
        self._cards_frame.grid(row=1, column=0, sticky="ew", padx=28, pady=(12, 0))
        self._card_widgets: dict = {}
        self._build_summary_cards()

        # ---- Alerts ------------------------------------------------
        self._alert_outer = tk.Frame(outer, bg=TM.c("bg_main"))
        self._bg_main_widgets.append(self._alert_outer)
        self._alert_outer.grid(row=2, column=0, sticky="ew", padx=28, pady=(16, 0))

        # ---- Chart + budget bars -----------------------------------
        chart_row = tk.Frame(outer, bg=TM.c("bg_main"))
        self._bg_main_widgets.append(chart_row)
        chart_row.grid(row=3, column=0, sticky="ew", padx=28, pady=(16, 0))
        chart_row.columnconfigure(0, weight=3)
        chart_row.columnconfigure(1, weight=2)

        # Left: chart frame
        self._chart_frame = tk.Frame(
            chart_row, bg=TM.c("bg_card"),
            highlightbackground=TM.c("border"), highlightthickness=1,
        )
        self._chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._bg_card_widgets.append(self._chart_frame)

        chart_toggle_bar = tk.Frame(self._chart_frame, bg=TM.c("bg_card"))
        self._bg_card_widgets.append(chart_toggle_bar)
        chart_toggle_bar.pack(fill="x", padx=12, pady=(10, 0))

        self._chart_title_lbl = tk.Label(
            chart_toggle_bar, text="Spending by Category",
            bg=TM.c("bg_card"), fg=TM.c("text_primary"), font=FONTS["heading3"],
        )
        self._chart_title_lbl.pack(side="left")
        self._text_p_labels.append(self._chart_title_lbl)
        self._bg_card_widgets.append(self._chart_title_lbl)

        ttk.Button(
            chart_toggle_bar, text="  Pie  ", style="Secondary.TButton",
            command=lambda: self._toggle_chart("pie"),
        ).pack(side="right", padx=(4, 0))
        ttk.Button(
            chart_toggle_bar, text="  Bar  ", style="Secondary.TButton",
            command=lambda: self._toggle_chart("bar"),
        ).pack(side="right")

        self._fig_placeholder = tk.Frame(self._chart_frame, bg=TM.c("bg_card"))
        self._fig_placeholder.pack(fill="both", expand=True, padx=12, pady=10)
        self._bg_card_widgets.append(self._fig_placeholder)

        # Right: budget bars
        self._bars_outer = tk.Frame(
            chart_row, bg=TM.c("bg_card"),
            highlightbackground=TM.c("border"), highlightthickness=1,
        )
        self._bars_outer.grid(row=0, column=1, sticky="nsew")
        self._bg_card_widgets.append(self._bars_outer)

        self._budget_title_lbl = tk.Label(
            self._bars_outer, text="Budget Usage",
            bg=TM.c("bg_card"), fg=TM.c("text_primary"), font=FONTS["heading3"],
        )
        self._budget_title_lbl.pack(anchor="w", padx=14, pady=(10, 4))
        self._text_p_labels.append(self._budget_title_lbl)
        self._bg_card_widgets.append(self._budget_title_lbl)

        self._bars_scroll_frame = tk.Frame(self._bars_outer, bg=TM.c("bg_card"))
        self._bars_scroll_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self._bg_card_widgets.append(self._bars_scroll_frame)

        # Bottom padding
        tk.Frame(outer, bg=TM.c("bg_main"), height=30).grid(row=4, column=0)

    def _build_summary_cards(self) -> None:
        """Create the three stat cards."""
        cards_def = [
            ("total_spent",  "Total Spent",      "\u20b90.00", TM.c("accent")),
            ("total_budget", "Total Budget",     "\u20b90.00", TM.c("success")),
            ("remaining",    "Remaining Budget", "\u20b90.00", TM.c("warning")),
        ]
        self._cards_frame.columnconfigure((0, 1, 2), weight=1)
        self._card_frames: list[dict] = []   # store references for theme updates

        for col, (key, label, default_val, color) in enumerate(cards_def):
            card = tk.Frame(
                self._cards_frame, bg=TM.c("bg_card"),
                highlightbackground=TM.c("border"), highlightthickness=1,
            )
            card.grid(row=0, column=col, sticky="ew",
                      padx=(0 if col == 0 else 8, 0), ipady=6)

            accent_bar = tk.Frame(card, bg=color, width=5)
            accent_bar.pack(side="left", fill="y")

            content = tk.Frame(card, bg=TM.c("bg_card"))
            content.pack(side="left", fill="both", expand=True, padx=16, pady=12)

            val_var = tk.StringVar(value=default_val)
            val_lbl = tk.Label(
                content, textvariable=val_var,
                bg=TM.c("bg_card"), fg=color, font=FONTS["heading2"],
            )
            val_lbl.pack(anchor="w")

            sub_lbl = tk.Label(
                content, text=label,
                bg=TM.c("bg_card"), fg=TM.c("text_secondary"), font=FONTS["small"],
            )
            sub_lbl.pack(anchor="w")

            self._card_widgets[key] = val_var
            self._card_frames.append({
                "card": card, "accent_bar": accent_bar,
                "content": content, "val_lbl": val_lbl,
                "sub_lbl": sub_lbl, "color": color,
            })

    # ------------------------------------------------------------------
    # Data update helpers
    # ------------------------------------------------------------------

    def _update_summary_cards(self, summary: dict) -> None:
        self._card_widgets["total_spent"].set(format_currency(summary["total_spent"]))
        self._card_widgets["total_budget"].set(format_currency(summary["total_budget"]))
        self._card_widgets["remaining"].set(format_currency(summary["remaining"]))

    def _update_alerts(self, statuses: list) -> None:
        if self._alert_inner and self._alert_inner.winfo_exists():
            self._alert_inner.destroy()

        over = [s for s in statuses if s["over_budget"]]
        if not over:
            return

        self._alert_inner = tk.Frame(self._alert_outer, bg=TM.c("bg_main"))
        self._alert_inner.pack(fill="x")

        tk.Label(
            self._alert_inner,
            text=f"⚠️  Budget Exceeded in {len(over)} categor{'y' if len(over)==1 else 'ies'}",
            bg=TM.c("bg_main"), fg=TM.c("danger"), font=FONTS["body_bold"],
        ).pack(anchor="w", pady=(0, 6))

        alert_card = tk.Frame(
            self._alert_inner, bg=TM.c("danger_light"),
            highlightbackground=TM.c("danger"), highlightthickness=1,
        )
        alert_card.pack(fill="x")

        for s in over:
            row = tk.Frame(alert_card, bg=TM.c("danger_light"))
            row.pack(fill="x", padx=14, pady=4)
            tk.Label(
                row,
                text=(
                    f"🔴  {s['category']}:  "
                    f"Spent {format_currency(s['spent'])} of "
                    f"{format_currency(s['limit'])} ({s['pct_used']:.0f}%)"
                ),
                bg=TM.c("danger_light"), fg=TM.c("danger"), font=FONTS["body_bold"],
            ).pack(side="left")

    def _update_budget_bars(self, statuses: list) -> None:
        for w in self._bars_scroll_frame.winfo_children():
            w.destroy()

        if not statuses:
            tk.Label(
                self._bars_scroll_frame,
                text="No budgets set.\nGo to Settings to add budgets.",
                bg=TM.c("bg_card"), fg=TM.c("text_secondary"),
                font=FONTS["body"], justify="center",
            ).pack(pady=20)
            return

        for s in statuses:
            row_f = tk.Frame(self._bars_scroll_frame, bg=TM.c("bg_card"))
            row_f.pack(fill="x", pady=4)

            info_r = tk.Frame(row_f, bg=TM.c("bg_card"))
            info_r.pack(fill="x")

            tk.Label(
                info_r, text=s["category"],
                bg=TM.c("bg_card"), fg=TM.c("text_primary"), font=FONTS["small_bold"],
                anchor="w",
            ).pack(side="left")

            color = TM.c("danger") if s["over_budget"] else TM.c("text_secondary")
            tk.Label(
                info_r,
                text=f"{format_currency(s['spent'])} / {format_currency(s['limit'])}",
                bg=TM.c("bg_card"), fg=color, font=FONTS["small"],
            ).pack(side="right")

            pct = min(s["pct_used"], 100)
            bar_style = (
                "Danger.Horizontal.TProgressbar" if s["over_budget"]
                else "Warning.Horizontal.TProgressbar" if pct >= 80
                else "TProgressbar"
            )
            ttk.Progressbar(
                row_f, orient="horizontal", mode="determinate",
                maximum=100, value=pct, style=bar_style,
            ).pack(fill="x", pady=(2, 0))

            tk.Frame(self._bars_scroll_frame, bg=TM.c("border"), height=1).pack(
                fill="x", pady=(4, 0)
            )

    def _draw_chart(self, expenses, budgets) -> None:
        if self._canvas_widget:
            self._canvas_widget.get_tk_widget().destroy()
            plt.close("all")

        for w in self._fig_placeholder.winfo_children():
            w.destroy()

        bg_card  = TM.c("bg_card")
        text_s   = TM.c("text_secondary")
        accent   = TM.c("accent")
        success  = TM.c("success")
        border   = TM.c("border")

        fig = Figure(figsize=(5, 3.8), dpi=96, facecolor=bg_card)
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg_card)

        if self._chart_type == "pie":
            labels, amounts = pie_chart_data(expenses)
            if labels:
                wedges, texts, autotexts = ax.pie(
                    amounts, labels=None, autopct="%1.1f%%",
                    colors=TM.chart_colors()[: len(labels)],
                    startangle=140, pctdistance=0.82,
                    wedgeprops={"linewidth": 2, "edgecolor": bg_card},
                )
                for at in autotexts:
                    at.set_fontsize(8)
                    at.set_color("#FFFFFF")
                ax.legend(
                    wedges, labels,
                    loc="lower center", bbox_to_anchor=(0.5, -0.18),
                    ncol=3, fontsize=7, frameon=False,
                    labelcolor=text_s,
                )
            else:
                ax.text(0.5, 0.5, "No expenses this month",
                        ha="center", va="center", transform=ax.transAxes,
                        color=text_s, fontsize=11)
                ax.axis("off")

        else:
            cats, spent_vals, limit_vals = bar_chart_data(expenses, budgets)
            if cats:
                x = range(len(cats))
                w = 0.38
                ax.bar([i - w / 2 for i in x], spent_vals, w,
                       label="Spent", color=accent, alpha=0.9)
                ax.bar([i + w / 2 for i in x], limit_vals, w,
                       label="Budget", color=success, alpha=0.6)
                ax.set_xticks(list(x))
                ax.set_xticklabels(
                    [c[:10] + "…" if len(c) > 10 else c for c in cats],
                    rotation=30, ha="right", fontsize=8, color=text_s,
                )
                ax.tick_params(axis="y", labelsize=8, colors=text_s)
                ax.spines[["top", "right"]].set_visible(False)
                ax.spines[["left", "bottom"]].set_color(border)
                ax.set_ylabel("Amount (\u20b9)", fontsize=9, color=text_s)
                ax.legend(fontsize=8, frameon=False, labelcolor=text_s)
                ax.yaxis.grid(True, linestyle="--", alpha=0.4, color=border)
                ax.set_axisbelow(True)
            else:
                ax.text(0.5, 0.5, "No data for this period",
                        ha="center", va="center", transform=ax.transAxes,
                        color=text_s, fontsize=11)
                ax.axis("off")

        fig.tight_layout(pad=1.2)

        canvas = FigureCanvasTkAgg(fig, master=self._fig_placeholder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._canvas_widget = canvas

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _toggle_chart(self, chart_type: str) -> None:
        self._chart_type = chart_type
        expenses = get_expenses_for_month(self._user_id, self._year, self._month)
        budgets  = get_all_budgets(self._user_id)
        self._draw_chart(expenses, budgets)

    def _on_month_change(self) -> None:
        raw = self._month_var.get()
        try:
            parts = raw.split()
            self._month = list(calendar.month_name).index(parts[0])
            self._year  = int(parts[1])
        except (ValueError, IndexError):
            pass
        self.refresh()

    def _download_pdf(self) -> None:
        """Prompt for a save path and generate the PDF report."""
        import tkinter.filedialog as fd
        from tkinter import messagebox as mb
        import calendar as _cal

        expenses = get_expenses_for_month(self._user_id, self._year, self._month)
        budgets  = get_all_budgets(self._user_id)

        if not expenses:
            mb.showwarning(
                "No Data",
                "There are no expenses for the selected month.\n"
                "Please select a month that has expense records.",
                parent=self,
            )
            return

        default_name = (
            f"Expense_Report_{self._year}_{self._month:02d}.pdf"
        )
        filepath = fd.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialfile=default_name,
            title="Save PDF Report",
            parent=self,
        )
        if not filepath:
            return

        period = f"{_cal.month_name[self._month]} {self._year}"
        try:
            from report_generator import generate_pdf_report
            count = generate_pdf_report(
                expenses=expenses,
                budgets=budgets,
                filepath=filepath,
                report_title=f"Expense Report — {period}",
                period_label=period,
            )
            mb.showinfo(
                "PDF Generated",
                f"Report saved successfully!\n\n"
                f"  Records : {count}\n"
                f"  Period  : {period}\n"
                f"  File    : {filepath}",
                parent=self,
            )
        except PermissionError:
            mb.showerror(
                "Permission Denied",
                f"Cannot write to:\n{filepath}\n\n"
                "Make sure the file is not open in another program.",
                parent=self,
            )
        except Exception as exc:
            mb.showerror(
                "PDF Generation Failed",
                f"An error occurred while generating the report:\n\n{exc}",
                parent=self,
            )

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        if not self.winfo_exists():
            TM.unregister(self._apply_theme)
            return

        bg_main = TM.c("bg_main")
        bg_card = TM.c("bg_card")
        text_p  = TM.c("text_primary")
        text_s  = TM.c("text_secondary")
        border  = TM.c("border")

        for w in self._bg_main_widgets:
            if w.winfo_exists():
                w.configure(bg=bg_main)
        for w in self._bg_card_widgets:
            if w.winfo_exists():
                w.configure(bg=bg_card)
                try:
                    w.configure(highlightbackground=border)
                except tk.TclError:
                    pass
        for lbl in self._text_p_labels:
            if lbl.winfo_exists():
                # figure out which bg this label is on
                parent_bg = bg_card if lbl.master in self._bg_card_widgets else bg_main
                lbl.configure(bg=parent_bg, fg=text_p)
        for lbl in self._text_s_labels:
            if lbl.winfo_exists():
                lbl.configure(bg=bg_main, fg=text_s)

        # Summary cards
        for info in self._card_frames:
            if info["card"].winfo_exists():
                info["card"].configure(bg=bg_card, highlightbackground=border)
                info["content"].configure(bg=bg_card)
                info["val_lbl"].configure(bg=bg_card)     # colour stays from definition
                info["sub_lbl"].configure(bg=bg_card, fg=text_s)

        self._scroll_canvas.configure(bg=bg_main)

        # Redraw chart with new colours
        expenses = get_expenses_for_month(self._user_id, self._year, self._month)
        budgets  = get_all_budgets(self._user_id)
        self._draw_chart(expenses, budgets)
        self._update_budget_bars(budget_status(expenses, budgets))
