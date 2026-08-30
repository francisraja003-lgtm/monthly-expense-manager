"""
theme.py — Dynamic theme manager supporting Light and Dark modes.

Architecture
------------
- ``ThemeManager`` is a module-level singleton (``TM``).
- All GUI files import ``TM`` and read colours via ``TM.c(key)``.
- The COLORS dict in styles.py is replaced by TM — no file-scope copy
  that would become stale after a toggle.
- When ``TM.toggle()`` is called, it:
    1. Swaps the active palette.
    2. Re-applies all ttk styles.
    3. Calls every registered callback so tab frames can re-colour their
       plain tk.* widgets (which don't participate in ttk styles).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------

_LIGHT: Dict[str, object] = {
    # Backgrounds
    "bg_main":    "#F0F4F8",
    "bg_sidebar": "#1E293B",
    "bg_card":    "#FFFFFF",
    "bg_input":   "#F8FAFC",

    # Accent
    "accent":       "#3B82F6",
    "accent_hover": "#2563EB",
    "accent_light": "#DBEAFE",

    # Status
    "success":      "#10B981",
    "warning":      "#F59E0B",
    "danger":       "#EF4444",
    "danger_light": "#FEE2E2",

    # Text
    "text_primary":   "#0F172A",
    "text_secondary": "#64748B",
    "text_on_accent": "#FFFFFF",
    "text_on_sidebar":"#CBD5E1",

    # Borders
    "border":       "#E2E8F0",
    "border_focus": "#3B82F6",

    # Chart colours
    "chart": [
        "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
        "#EC4899", "#06B6D4", "#84CC16", "#F97316", "#6366F1",
    ],
}

_DARK: Dict[str, object] = {
    # Backgrounds
    "bg_main":    "#0F172A",
    "bg_sidebar": "#020617",
    "bg_card":    "#1E293B",
    "bg_input":   "#334155",

    # Accent (same vivid blue works on dark bg)
    "accent":       "#3B82F6",
    "accent_hover": "#60A5FA",
    "accent_light": "#1E3A5F",

    # Status
    "success":      "#10B981",
    "warning":      "#F59E0B",
    "danger":       "#F87171",
    "danger_light": "#3B1F1F",

    # Text
    "text_primary":   "#F1F5F9",
    "text_secondary": "#94A3B8",
    "text_on_accent": "#FFFFFF",
    "text_on_sidebar":"#CBD5E1",

    # Borders
    "border":       "#334155",
    "border_focus": "#60A5FA",

    # Chart colours (slightly brighter for dark backgrounds)
    "chart": [
        "#60A5FA", "#34D399", "#FBBF24", "#F87171", "#A78BFA",
        "#F472B6", "#22D3EE", "#A3E635", "#FB923C", "#818CF8",
    ],
}

# ---------------------------------------------------------------------------
# Fonts  (shared across themes)
# ---------------------------------------------------------------------------

FONTS: Dict[str, tuple] = {
    "heading1":   ("Segoe UI", 22, "bold"),
    "heading2":   ("Segoe UI", 16, "bold"),
    "heading3":   ("Segoe UI", 13, "bold"),
    "body":       ("Segoe UI", 11),
    "body_bold":  ("Segoe UI", 11, "bold"),
    "small":      ("Segoe UI", 9),
    "small_bold": ("Segoe UI", 9, "bold"),
    "mono":       ("Consolas", 10),
    "sidebar_item":("Segoe UI", 12),
}

TREE_ROW_HEIGHT = 32   # px — enough vertical space so text never touches cell edges


# ---------------------------------------------------------------------------
# ThemeManager
# ---------------------------------------------------------------------------

class ThemeManager:
    """
    Singleton that owns the active colour palette and re-styles the app
    on demand.

    Usage::

        from gui.theme import TM, FONTS
        bg = TM.c("bg_card")            # read a colour
        TM.register(callback)           # called after every toggle
        TM.toggle(style, root)          # flip light ↔ dark
    """

    def __init__(self) -> None:
        self._mode: str = "light"
        self._palette: Dict[str, object] = dict(_LIGHT)
        self._callbacks: List[Callable[[], None]] = []
        self._style: Optional[ttk.Style] = None
        self._root: Optional[tk.Tk] = None

    # ------------------------------------------------------------------
    # Colour access
    # ------------------------------------------------------------------

    def c(self, key: str) -> str:
        """Return the colour string for *key* from the active palette."""
        return self._palette[key]  # type: ignore[return-value]

    def chart_colors(self) -> List[str]:
        """Return the list of chart colours for the active palette."""
        return self._palette["chart"]  # type: ignore[return-value]

    @property
    def is_dark(self) -> bool:
        """True when dark mode is active."""
        return self._mode == "dark"

    @property
    def mode(self) -> str:
        """'light' or 'dark'."""
        return self._mode

    # ------------------------------------------------------------------
    # Setup (called once from main.py)
    # ------------------------------------------------------------------

    def setup(self, root: tk.Tk) -> ttk.Style:
        """
        Initialise the ttk.Style and store a reference to the root window.

        Args:
            root: The application's Tk root window.

        Returns:
            The configured ttk.Style instance.
        """
        self._root = root
        self._style = ttk.Style(root)
        self._style.theme_use("clam")
        self._apply_ttk_styles()
        return self._style

    # ------------------------------------------------------------------
    # Toggle
    # ------------------------------------------------------------------

    def toggle(self) -> None:
        """
        Switch between light and dark mode.

        Re-applies all ttk styles and fires all registered callbacks so
        plain tk.* widgets can update their bg/fg.
        """
        if self._mode == "light":
            self._mode = "dark"
            self._palette = dict(_DARK)
        else:
            self._mode = "light"
            self._palette = dict(_LIGHT)

        if self._root:
            self._root.configure(bg=self.c("bg_main"))

        if self._style:
            self._apply_ttk_styles()

        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                pass  # Never crash the app because of a stale callback

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def register(self, callback: Callable[[], None]) -> None:
        """
        Register a zero-argument callable that will be called after each
        theme toggle to let a widget/frame re-colour itself.
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister(self, callback: Callable[[], None]) -> None:
        """Remove a previously registered callback."""
        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Internal: rebuild all ttk styles
    # ------------------------------------------------------------------

    def _apply_ttk_styles(self) -> None:
        """Configure every named ttk style from the current palette."""
        s = self._style
        p = self._palette  # shorthand

        # ---- Frames ------------------------------------------------
        s.configure("TFrame",        background=p["bg_main"])
        s.configure("Card.TFrame",   background=p["bg_card"], relief="flat")
        s.configure("TLabelframe",   background=p["bg_card"],
                    bordercolor=p["border"], relief="groove")
        s.configure("TLabelframe.Label", background=p["bg_card"],
                    foreground=p["text_primary"], font=FONTS["body_bold"])

        # ---- Labels ------------------------------------------------
        s.configure("TLabel",         background=p["bg_main"],
                    foreground=p["text_primary"], font=FONTS["body"])
        s.configure("Card.TLabel",    background=p["bg_card"],
                    foreground=p["text_primary"], font=FONTS["body"])
        s.configure("Heading.TLabel", background=p["bg_main"],
                    foreground=p["text_primary"], font=FONTS["heading2"])
        s.configure("Subheading.TLabel", background=p["bg_main"],
                    foreground=p["text_secondary"], font=FONTS["body"])
        s.configure("Danger.TLabel",  background=p["bg_card"],
                    foreground=p["danger"], font=FONTS["body_bold"])
        s.configure("Success.TLabel", background=p["bg_card"],
                    foreground=p["success"], font=FONTS["body_bold"])

        # ---- Buttons -----------------------------------------------
        s.configure("Accent.TButton",
                    background=p["accent"], foreground=p["text_on_accent"],
                    font=FONTS["body_bold"], borderwidth=0, focusthickness=0,
                    padding=(16, 9))
        s.map("Accent.TButton",
              background=[("active", p["accent_hover"]), ("pressed", p["accent_hover"])],
              foreground=[("active", p["text_on_accent"])])

        s.configure("Danger.TButton",
                    background=p["danger"], foreground=p["text_on_accent"],
                    font=FONTS["body_bold"], borderwidth=0, padding=(16, 9))
        s.map("Danger.TButton",
              background=[("active", "#DC2626"), ("pressed", "#DC2626")])

        s.configure("Secondary.TButton",
                    background=p["bg_card"], foreground=p["text_primary"],
                    font=FONTS["body"], borderwidth=1, relief="solid",
                    padding=(16, 9))
        s.map("Secondary.TButton",
              background=[("active", p["accent_light"])],
              foreground=[("active", p["text_primary"])],
              bordercolor=[("!active", p["border"]), ("active", p["accent"])])

        # ---- Entry / Combobox --------------------------------------
        s.configure("TEntry",
                    fieldbackground=p["bg_input"], foreground=p["text_primary"],
                    bordercolor=p["border"], insertcolor=p["text_primary"],
                    font=FONTS["body"], padding=6)
        s.map("TEntry",
              bordercolor=[("focus", p["border_focus"])],
              lightcolor=[("focus", p["border_focus"])])

        s.configure("TCombobox",
                    fieldbackground=p["bg_input"], foreground=p["text_primary"],
                    selectbackground=p["accent_light"],
                    selectforeground=p["text_primary"],
                    font=FONTS["body"], padding=6)
        s.map("TCombobox",
              fieldbackground=[("readonly", p["bg_input"])],
              foreground=[("readonly", p["text_primary"])])

        # ---- Notebook ----------------------------------------------
        s.configure("TNotebook",     background=p["bg_main"], borderwidth=0)
        s.configure("TNotebook.Tab", background=p["bg_card"],
                    foreground=p["text_secondary"], font=FONTS["body"],
                    padding=(16, 8))
        s.map("TNotebook.Tab",
              background=[("selected", p["accent"]),
                          ("active",   p["accent_light"]),
                          ("disabled", p["bg_main"])],
              foreground=[("selected",  p["text_on_accent"]),
                          ("active",    p["text_primary"]),
                          ("disabled",  p["text_secondary"])])

        # ---- Treeview ----------------------------------------------
        s.configure("Treeview",
                    background=p["bg_card"], fieldbackground=p["bg_card"],
                    foreground=p["text_primary"], rowheight=TREE_ROW_HEIGHT,
                    font=FONTS["body"], borderwidth=0)
        s.configure("Treeview.Heading",
                    background=p["accent_light"], foreground=p["accent"],
                    font=FONTS["body_bold"], relief="flat", padding=(10, 8))
        s.map("Treeview",
              background=[("selected", p["accent"])],
              foreground=[("selected", p["text_on_accent"])],
              fieldbackground=[("!selected", p["bg_card"])])
        s.map("Treeview.Heading",
              background=[("active", p["accent_light"])])

        # ---- Scrollbar ---------------------------------------------
        s.configure("TScrollbar",
                    background=p["bg_input"],
                    troughcolor=p["bg_card"],
                    borderwidth=0,
                    arrowsize=12,
                    arrowcolor=p["text_secondary"])

        # ---- Checkbutton -------------------------------------------
        s.configure("TCheckbutton",
                    background=p["bg_card"],
                    foreground=p["text_primary"],
                    font=FONTS["body"])
        s.map("TCheckbutton",
              background=[("active", p["bg_card"])],
              foreground=[("active", p["text_primary"])])

        # ---- Separator ---------------------------------------------
        s.configure("TSeparator", background=p["border"])

        # ---- Progressbar -------------------------------------------
        s.configure("TProgressbar",
                    troughcolor=p["border"], background=p["accent"], thickness=10)
        s.configure("Danger.Horizontal.TProgressbar",
                    troughcolor=p["border"], background=p["danger"], thickness=10)
        s.configure("Warning.Horizontal.TProgressbar",
                    troughcolor=p["border"], background=p["warning"], thickness=10)


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------

TM = ThemeManager()

# Keep COLORS as a thin compatibility shim so existing code that imports
# ``from gui.styles import COLORS`` still works without modification.
# It is a live view because it points to TM's internal dict.
# (styles.py is updated to re-export TM.c instead of the static dict.)
COLORS = _LIGHT   # kept for styles.py backward compat import
