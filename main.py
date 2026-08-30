"""
main.py — Application entry point.

Flow:
  1. Root Tk window is created (hidden).
  2. DB is initialised.
  3. AuthWindow is shown — user must log in or sign up.
  4. On success, the main app window is built for that user.
  5. A theme toggle button and logout button live in the header bar.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database import initialize_db
from models import User
from gui.theme import TM, FONTS
from gui.styles import apply_styles          # now delegates to TM
from gui.auth import AuthWindow
from gui.add_expense_tab import AddExpenseTab
from gui.view_expenses_tab import ViewExpensesTab
from gui.dashboard_tab import DashboardTab
from gui.settings_tab import SettingsTab


class ExpenseManagerApp:
    """
    Orchestrator that owns the root Tk window and the main content frame.

    The class is intentionally *not* a tk.Tk subclass so that we can
    destroy and recreate the content area on logout without destroying
    the root window (which would end the mainloop).
    """

    def __init__(self) -> None:
        # ---- Root window (hidden until auth completes) -------------
        self._root = tk.Tk()
        self._root.withdraw()          # hide while auth runs
        self._root.title("Personal Expense & Budget Manager")
        self._root.minsize(960, 640)
        # Start maximised on Windows; falls back gracefully on other OS
        try:
            self._root.state("zoomed")
        except tk.TclError:
            sw = self._root.winfo_screenwidth()
            sh = self._root.winfo_screenheight()
            self._root.geometry(f"{sw}x{sh}+0+0")

        try:
            self._root.iconbitmap("icon.ico")
        except Exception:
            pass

        # ---- DB + styles ------------------------------------------
        initialize_db()
        apply_styles(self._root)
        self._root.configure(bg=TM.c("bg_main"))

        # ---- Auth gate --------------------------------------------
        self._current_user: User | None = None
        self._main_frame: tk.Frame | None = None
        self._show_auth()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _show_auth(self) -> None:
        """Display the Login/Signup window; called at startup and after logout."""
        AuthWindow(self._root, on_success=self._on_auth_success)

    def _on_auth_success(self, user: User) -> None:
        """Called by AuthWindow after a successful login or signup."""
        self._current_user = user
        self._build_main_ui()
        # Centre and show the main window
        self._root.deiconify()
        self._center_window()

    # ------------------------------------------------------------------
    # Main UI
    # ------------------------------------------------------------------

    def _build_main_ui(self) -> None:
        """Build (or rebuild after logout) the full app UI for the logged-in user."""
        # Destroy any existing content (e.g. after re-login)
        if self._main_frame and self._main_frame.winfo_exists():
            self._main_frame.destroy()

        self._main_frame = tk.Frame(self._root, bg=TM.c("bg_main"))
        self._main_frame.pack(fill="both", expand=True)

        # ---- Header bar --------------------------------------------
        self._header = tk.Frame(
            self._main_frame, bg=TM.c("bg_sidebar"), height=58
        )
        self._header.pack(fill="x", side="top")
        self._header.pack_propagate(False)

        # App title (left)
        self._title_lbl = tk.Label(
            self._header,
            text="💰  Expense & Budget Manager",
            bg=TM.c("bg_sidebar"),
            fg=TM.c("text_on_accent"),
            font=FONTS["heading2"],
        )
        self._title_lbl.pack(side="left", padx=24, pady=10)

        # Right-side controls
        right_frame = tk.Frame(self._header, bg=TM.c("bg_sidebar"))
        right_frame.pack(side="right", padx=14, pady=8)

        # User greeting
        display = self._current_user.display_name or self._current_user.username
        self._user_lbl = tk.Label(
            right_frame,
            text=f"👤  {display}",
            bg=TM.c("bg_sidebar"),
            fg=TM.c("text_on_sidebar"),
            font=FONTS["small"],
        )
        self._user_lbl.pack(side="left", padx=(0, 14))

        # Theme toggle button
        self._theme_btn = tk.Label(
            right_frame,
            text=self._theme_icon(),
            bg=TM.c("bg_sidebar"),
            fg=TM.c("text_on_accent"),
            font=("Segoe UI", 16),
            cursor="hand2",
            padx=6,
        )
        self._theme_btn.pack(side="left", padx=(0, 8))
        self._theme_btn.bind("<Button-1>", lambda _e: self._toggle_theme())
        self._theme_btn.bind("<Enter>",
                             lambda _e: self._theme_btn.config(fg=TM.c("accent_hover")))
        self._theme_btn.bind("<Leave>",
                             lambda _e: self._theme_btn.config(fg=TM.c("text_on_accent")))

        # Logout button
        self._logout_btn = tk.Label(
            right_frame,
            text="⎋  Logout",
            bg=TM.c("bg_sidebar"),
            fg=TM.c("text_on_sidebar"),
            font=FONTS["small"],
            cursor="hand2",
            padx=8, pady=4,
            relief="flat",
        )
        self._logout_btn.pack(side="left")
        self._logout_btn.bind("<Button-1>", lambda _e: self._logout())
        self._logout_btn.bind(
            "<Enter>", lambda _e: self._logout_btn.config(fg=TM.c("danger"))
        )
        self._logout_btn.bind(
            "<Leave>", lambda _e: self._logout_btn.config(fg=TM.c("text_on_sidebar"))
        )

        # ---- Notebook with four tabs --------------------------------
        uid = self._current_user.id

        self._notebook = ttk.Notebook(self._main_frame, style="TNotebook")
        self._notebook.pack(fill="both", expand=True)

        self._dashboard_tab = DashboardTab(self._notebook, user_id=uid)
        self._add_tab = AddExpenseTab(
            self._notebook, user_id=uid,
            on_expense_added=self._on_data_changed,
        )
        self._view_tab = ViewExpensesTab(
            self._notebook, user_id=uid,
            on_data_changed=self._on_data_changed,
        )
        self._settings_tab = SettingsTab(
            self._notebook, user_id=uid,
            on_data_changed=self._on_data_changed,
        )

        self._notebook.add(self._dashboard_tab, text=" 📊  Dashboard ")
        self._notebook.add(self._add_tab,        text=" ➕  Add Expense ")
        self._notebook.add(self._view_tab,        text=" 📋  View / Manage ")
        self._notebook.add(self._settings_tab,    text=" ⚙️  Settings ")

        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Register for theme updates (header bar plain-tk widgets)
        TM.register(self._apply_header_theme)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_data_changed(self) -> None:
        """Called after any expense/budget mutation to keep tabs in sync."""
        self._view_tab.refresh()
        self._dashboard_tab.refresh()

    def _on_tab_changed(self, _event: tk.Event) -> None:
        """Refresh the Dashboard when the user switches to it."""
        try:
            selected = self._notebook.index(self._notebook.select())
            if selected == 0:
                self._dashboard_tab.refresh()
        except tk.TclError:
            pass

    def _toggle_theme(self) -> None:
        """Switch between light and dark mode."""
        TM.toggle()
        self._theme_btn.config(text=self._theme_icon())

    def _logout(self) -> None:
        """Confirm, tear down the main UI, and return to the auth screen."""
        if not messagebox.askyesno(
            "Logout",
            "Log out of your account?\nUnsaved changes will be lost.",
            parent=self._root,
        ):
            return

        # Clean up
        TM.unregister(self._apply_header_theme)
        if self._main_frame and self._main_frame.winfo_exists():
            self._main_frame.destroy()
        self._current_user = None
        self._root.withdraw()
        self._show_auth()

    # ------------------------------------------------------------------
    # Theme helpers
    # ------------------------------------------------------------------

    def _theme_icon(self) -> str:
        """Return the emoji icon for the current (next) theme state."""
        return "🌙" if not TM.is_dark else "☀️"

    def _apply_header_theme(self) -> None:
        """Re-colour the header bar widgets after a theme change."""
        if not self._main_frame or not self._main_frame.winfo_exists():
            return
        bg_sb   = TM.c("bg_sidebar")
        fg_on   = TM.c("text_on_accent")
        fg_side = TM.c("text_on_sidebar")

        self._header.configure(bg=bg_sb)
        self._title_lbl.configure(bg=bg_sb, fg=fg_on)

        # right_frame is the immediate parent of the user/theme/logout labels
        for widget in self._header.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=bg_sb)

        self._user_lbl.configure(bg=bg_sb, fg=fg_side)
        self._theme_btn.configure(bg=bg_sb, fg=fg_on, text=self._theme_icon())
        self._logout_btn.configure(bg=bg_sb, fg=fg_side)
        self._main_frame.configure(bg=TM.c("bg_main"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _center_window(self) -> None:
        """Ensure window is maximised after auth completes."""
        try:
            self._root.state("zoomed")
        except tk.TclError:
            self._root.update_idletasks()
            sw = self._root.winfo_screenwidth()
            sh = self._root.winfo_screenheight()
            self._root.geometry(f"{sw}x{sh}+0+0")

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self._root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Create and run the application."""
    app = ExpenseManagerApp()
    app.run()


if __name__ == "__main__":
    main()
