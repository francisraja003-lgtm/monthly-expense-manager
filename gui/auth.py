"""
auth.py — Login / Sign-up window.

Full-screen centered card layout.  Each form field uses simple sequential
pack() rows so nothing can appear out of order.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

from models import User
from operations import authenticate_user, create_user, get_user_by_username
from gui.theme import TM, FONTS


class AuthWindow(tk.Toplevel):
    """
    Full-screen modal Login / Sign-up window displayed before the main app.

    Args:
        master:     The hidden root Tk window.
        on_success: Callback invoked with the authenticated User on success.
    """

    def __init__(self, master: tk.Tk, on_success: Callable[[User], None]) -> None:
        super().__init__(master)
        self._master     = master
        self._on_success = on_success
        self._mode: str  = "login"

        self.title("Expense Manager — Sign In")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.grab_set()

        # Full-screen maximised, but still has a title bar
        self.state("zoomed")
        self.resizable(True, True)

        # Instance-level lists (avoid class-level mutable default)
        self._login_hint_frames:  list = []
        self._signup_hint_frames: list = []

        self._build_ui()
        self._apply_theme()
        TM.register(self._apply_theme)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── Outer canvas so the card stays centred as window resizes ──
        self._bg_canvas = tk.Canvas(self, highlightthickness=0)
        self._bg_canvas.pack(fill="both", expand=True)
        self._bg_canvas.bind("<Configure>", self._on_canvas_resize)

        # ── Card frame (placed manually by _on_canvas_resize) ─────────
        self._card_frame = tk.Frame(
            self._bg_canvas,
            highlightthickness=1,
        )

        # ── Brand strip inside the card ────────────────────────────────
        self._brand = tk.Frame(self._card_frame, height=68)
        self._brand.pack(fill="x")
        self._brand.pack_propagate(False)

        self._brand_lbl = tk.Label(
            self._brand,
            text="\U0001F4B0   Expense & Budget Manager",
            font=FONTS["heading2"],
        )
        self._brand_lbl.pack(expand=True)

        # ── Tab toggle row ─────────────────────────────────────────────
        tab_row = tk.Frame(self._card_frame)
        tab_row.pack(fill="x", padx=40, pady=(28, 0))
        self._tab_row = tab_row

        self._login_tab = tk.Label(
            tab_row, text="Sign In",
            font=FONTS["body_bold"], padx=18, pady=8, cursor="hand2",
        )
        self._login_tab.pack(side="left")
        self._login_tab.bind("<Button-1>", lambda _e: self._switch("login"))

        self._signup_tab = tk.Label(
            tab_row, text="Create Account",
            font=FONTS["body_bold"], padx=18, pady=8, cursor="hand2",
        )
        self._signup_tab.pack(side="left")
        self._signup_tab.bind("<Button-1>", lambda _e: self._switch("signup"))

        # sliding underline
        self._underline = tk.Frame(tab_row, height=3)
        self._underline.place(x=0, y=36, width=88, height=3)

        # ── Thin separator ─────────────────────────────────────────────
        self._sep = ttk.Separator(self._card_frame, orient="horizontal")
        self._sep.pack(fill="x", padx=40, pady=(2, 0))

        # ── Form container (login & signup packed on top of each other)
        self._form_host = tk.Frame(self._card_frame)
        self._form_host.pack(fill="x", padx=40, pady=(0, 28))

        self._build_login_form()
        self._build_signup_form()

        # ── Footer text ────────────────────────────────────────────────
        self._footer = tk.Label(
            self._bg_canvas,
            text="Your data is stored locally and never uploaded.",
            font=FONTS["small"],
        )
        self._footer_id = self._bg_canvas.create_window(0, 0, window=self._footer, anchor="n")

        # Store the card's canvas window id so we can move it on resize
        # without creating a new item every time (prevents item leak)
        self._card_win_id = self._bg_canvas.create_window(
            0, 0, window=self._card_frame, anchor="center"
        )

        self._switch("login")

        # Bind Enter → submit
        self.bind_all("<Return>", self._on_enter)

    # ------------------------------------------------------------------
    # Login form  (all pack-based, strict order)
    # ------------------------------------------------------------------

    def _build_login_form(self) -> None:
        f = tk.Frame(self._form_host)
        self._login_frame = f

        self._login_user_var = tk.StringVar()
        self._login_pass_var = tk.StringVar()

        self._field(f, "Username", self._login_user_var)
        self._field(f, "Password", self._login_pass_var, show="\u25CF")

        # Remember me
        rem = tk.Frame(f)
        rem.pack(fill="x", pady=(6, 0))
        self._rem_frame = rem
        self._remember_var = tk.BooleanVar(value=False)
        self._rem_chk = ttk.Checkbutton(rem, text="Remember me", variable=self._remember_var)
        self._rem_chk.pack(side="left")

        # Submit
        self._login_btn_submit = ttk.Button(
            f, text="   Sign In  \u2192   ",
            style="Accent.TButton", command=self._do_login,
        )
        self._login_btn_submit.pack(fill="x", pady=(22, 4), ipady=6)

        # Switch hint
        hint = tk.Frame(f)
        hint.pack(fill="x")
        self._login_hint_frames.append(hint)
        tk.Label(hint, text="Don't have an account?", font=FONTS["small"]).pack(side="left")
        lnk = tk.Label(hint, text="  Create one", font=FONTS["small"], cursor="hand2")
        lnk.pack(side="left")
        lnk.bind("<Button-1>", lambda _e: self._switch("signup"))
        self._login_link = lnk

    # ------------------------------------------------------------------
    # Sign-up form  (all pack-based, strict order)
    # ------------------------------------------------------------------

    def _build_signup_form(self) -> None:
        f = tk.Frame(self._form_host)
        self._signup_frame = f

        self._su_display_var = tk.StringVar()
        self._su_user_var    = tk.StringVar()
        self._su_pass_var    = tk.StringVar()
        self._su_pass2_var   = tk.StringVar()

        self._field(f, "Display Name (optional)", self._su_display_var)
        self._field(f, "Username *",               self._su_user_var)
        self._field(f, "Password *",               self._su_pass_var,  show="\u25CF")
        self._field(f, "Confirm Password *",       self._su_pass2_var, show="\u25CF")

        self._signup_btn_submit = ttk.Button(
            f, text="   Create Account  \u2192   ",
            style="Accent.TButton", command=self._do_signup,
        )
        self._signup_btn_submit.pack(fill="x", pady=(22, 4), ipady=6)

        hint = tk.Frame(f)
        hint.pack(fill="x")
        self._signup_hint_frames.append(hint)
        tk.Label(hint, text="Already have an account?", font=FONTS["small"]).pack(side="left")
        lnk = tk.Label(hint, text="  Sign in", font=FONTS["small"], cursor="hand2")
        lnk.pack(side="left")
        lnk.bind("<Button-1>", lambda _e: self._switch("login"))
        self._signup_link = lnk

    # helper called before _build_login/signup_form so lists exist
    # NOTE: initialised as instance variables in __init__ to avoid the
    # class-level mutable default anti-pattern.

    def _field(
        self,
        parent: tk.Frame,
        label: str,
        var: tk.StringVar,
        show: str = "",
    ) -> ttk.Entry:
        """Pack a label + entry pair vertically."""
        lbl = tk.Label(parent, text=label, font=FONTS["small_bold"], anchor="w")
        lbl.pack(fill="x", pady=(14, 3))

        entry = ttk.Entry(parent, textvariable=var, font=FONTS["body"], show=show)
        entry.pack(fill="x", ipady=5)
        return entry

    # ------------------------------------------------------------------
    # Mode switch
    # ------------------------------------------------------------------

    def _switch(self, mode: str) -> None:
        self._mode = mode
        if mode == "login":
            self._signup_frame.pack_forget()
            self._login_frame.pack(fill="x")
            self._login_tab.config(fg=TM.c("accent"))
            self._signup_tab.config(fg=TM.c("text_secondary"))
            self._underline.place(x=0, y=36, width=88)
        else:
            self._login_frame.pack_forget()
            self._signup_frame.pack(fill="x")
            self._signup_tab.config(fg=TM.c("accent"))
            self._login_tab.config(fg=TM.c("text_secondary"))
            self._underline.place(x=88, y=36, width=132)

    # ------------------------------------------------------------------
    # Canvas resize → re-centre card
    # ------------------------------------------------------------------

    def _on_canvas_resize(self, event: tk.Event) -> None:
        cw, ch = event.width, event.height
        card_w = min(500, int(cw * 0.90))

        # Move the existing canvas window item — never create a new one
        self._bg_canvas.coords(self._card_win_id, cw // 2, ch // 2)
        self._bg_canvas.itemconfig(self._card_win_id, width=card_w)
        self._card_frame.config(width=card_w)

        # Reposition footer
        self._bg_canvas.coords(self._footer_id, cw // 2, ch - 28)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_enter(self, _event=None) -> None:
        # Guard: don't fire if this window has already been destroyed
        if not self.winfo_exists():
            return
        if self._mode == "login":
            self._do_login()
        else:
            self._do_signup()

    def _do_login(self) -> None:
        if not self.winfo_exists():
            return
        username = self._login_user_var.get().strip()
        password = self._login_pass_var.get()

        if not username:
            messagebox.showerror("Missing Field", "Please enter your username.", parent=self)
            return
        if not password:
            messagebox.showerror("Missing Field", "Please enter your password.", parent=self)
            return

        user = authenticate_user(username, password)
        if user is None:
            messagebox.showerror(
                "Sign In Failed",
                "Incorrect username or password.\n\nNo account yet? Click 'Create Account'.",
                parent=self,
            )
            self._login_pass_var.set("")
            return
        self._succeed(user)

    def _do_signup(self) -> None:
        if not self.winfo_exists():
            return
        display  = self._su_display_var.get().strip()
        username = self._su_user_var.get().strip()
        password = self._su_pass_var.get()
        confirm  = self._su_pass2_var.get()

        if not username:
            messagebox.showerror("Missing Field", "Username is required.", parent=self)
            return
        if len(username) < 3:
            messagebox.showerror("Invalid Username",
                                 "Username must be at least 3 characters.", parent=self)
            return
        if not password:
            messagebox.showerror("Missing Field", "Password is required.", parent=self)
            return
        if len(password) < 6:
            messagebox.showerror("Weak Password",
                                 "Password must be at least 6 characters.", parent=self)
            return
        if password != confirm:
            messagebox.showerror("Password Mismatch", "Passwords do not match.", parent=self)
            self._su_pass2_var.set("")
            return
        if get_user_by_username(username) is not None:
            messagebox.showerror(
                "Username Taken",
                f"'{username}' is already registered. Choose a different username.",
                parent=self,
            )
            return

        try:
            user = create_user(username, password, display_name=display or username)
        except ValueError as exc:
            messagebox.showerror("Sign Up Failed", str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc), parent=self)
            return

        messagebox.showinfo(
            "Account Created!",
            f"Welcome, {user.display_name}!\nYou are now signed in.",
            parent=self,
        )
        self._succeed(user)

    def _succeed(self, user: User) -> None:
        TM.unregister(self._apply_theme)
        # Unbind Return so it can't fire again after window is gone
        try:
            self.unbind_all("<Return>")
        except Exception:
            pass
        self.destroy()
        self._on_success(user)

    def _on_close(self) -> None:
        self._master.destroy()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        if not self.winfo_exists():
            return

        bg_main = TM.c("bg_main")
        bg_sb   = TM.c("bg_sidebar")
        bg_card = TM.c("bg_card")
        text_p  = TM.c("text_primary")
        text_s  = TM.c("text_secondary")
        accent  = TM.c("accent")
        border  = TM.c("border")

        self.configure(bg=bg_main)
        self._bg_canvas.configure(bg=bg_main)

        self._card_frame.configure(bg=bg_card, highlightbackground=border,
                                   highlightcolor=border)
        self._brand.configure(bg=bg_sb)
        self._brand_lbl.configure(bg=bg_sb, fg=TM.c("text_on_accent"))

        self._tab_row.configure(bg=bg_card)
        self._form_host.configure(bg=bg_card)

        self._login_tab.configure(
            bg=bg_card,
            fg=accent if self._mode == "login" else text_s,
        )
        self._signup_tab.configure(
            bg=bg_card,
            fg=accent if self._mode == "signup" else text_s,
        )
        self._underline.configure(bg=accent)

        self._footer.configure(bg=bg_main, fg=text_s)

        # Walk both form frames
        for frame in (self._login_frame, self._signup_frame):
            _recolor_frame(frame, bg_card, text_p, text_s)

        # Hint row link labels keep accent colour
        self._login_link.configure(fg=accent)
        self._signup_link.configure(fg=accent)

        # Checkbox row
        self._rem_frame.configure(bg=bg_card)

        # Remember-me hint frames
        for fr in self._login_hint_frames + self._signup_hint_frames:
            if fr.winfo_exists():
                fr.configure(bg=bg_card)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

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
