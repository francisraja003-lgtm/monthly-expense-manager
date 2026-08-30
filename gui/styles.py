"""
styles.py — Backward-compatibility shim.

All theming is now managed by ``gui.theme.TM`` (ThemeManager).
This file re-exports the helpers that existing code imports so that
no other file needs a search-and-replace for the migration.

  from gui.styles import COLORS, FONTS, apply_styles
  ↓ now resolves to the live theme manager
"""

from gui.theme import TM, FONTS, TREE_ROW_HEIGHT   # noqa: F401
import tkinter as tk
from tkinter import ttk


# COLORS is kept as a module attribute that proxies TM so that code which
# does  ``COLORS["bg_card"]``  still works.  Because dicts are mutable and
# both _LIGHT and _DARK share the same keys, we expose TM's internal palette
# dict directly (it gets swapped on toggle).
class _ColorProxy:
    """
    Transparent proxy for TM's palette so that ``COLORS["key"]`` always
    reads the *current* theme value without needing an import update.
    """
    def __getitem__(self, key: str) -> str:
        return TM.c(key)

    def get(self, key: str, default=None):
        try:
            return TM.c(key)
        except KeyError:
            return default


COLORS = _ColorProxy()


def apply_styles(root: tk.Tk) -> ttk.Style:
    """
    Initialise and return the global ttk.Style via ThemeManager.

    This is called once in main.py; after that TM owns the style object.
    """
    return TM.setup(root)
