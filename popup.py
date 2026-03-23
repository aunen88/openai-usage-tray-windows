"""Tkinter settings window for OpenAI Usage Tray — Windows."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from config import Settings, save_settings
import win32_ui

# Typography
FONT    = ("Segoe UI", 10)
FONT_B  = ("Segoe UI Semibold", 10)
FONT_SM = ("Segoe UI", 8)


def _palette() -> dict:
    light = win32_ui.is_light_theme()
    return {
        "BG":      "#f3f3f3" if light else "#202020",
        "BG_SEC":  "#e8e8e8" if light else "#2c2c2c",
        "FG":      "#1c1c1c" if light else "#f0f0f0",
        "RED":     "#FF3B30",
        "BLUE":    "#007AFF",
    }


class SettingsWindow(tk.Toplevel):
    """Modal settings window. Calls on_save(new_settings) on successful save."""

    def __init__(
        self,
        master: tk.Tk,
        settings: Settings,
        on_save: Callable[[Settings], None],
    ) -> None:
        super().__init__(master)
        self.title("Settings — OpenAI Usage Tray")
        self.resizable(False, False)
        self._settings = settings
        self._on_save = on_save
        self._show_key = False
        self._p = _palette()
        self.configure(bg=self._p["BG"])
        self._build_ui()
        self.grab_set()
        self.focus_set()
        self.update_idletasks()
        self._center()
        try:
            win32_ui.apply_rounded_corners(self.winfo_id())
        except Exception:
            pass

    def _center(self) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_ui(self) -> None:
        PAD = 16
        p = self._p

        # ── API Key ──────────────────────────────────────────────────────────
        tk.Label(self, text="OpenAI Admin API Key", bg=p["BG"], fg=p["FG"],
                 font=FONT_B).pack(anchor="w", padx=PAD, pady=(PAD, 2))

        key_frame = tk.Frame(self, bg=p["BG"])
        key_frame.pack(fill="x", padx=PAD, pady=(0, 2))

        self._key_var = tk.StringVar(value=self._settings.api_key)
        self._key_entry = tk.Entry(
            key_frame, textvariable=self._key_var, show="●", width=36,
            bg=p["BG_SEC"], fg=p["FG"], insertbackground=p["FG"],
            relief="flat", font=FONT,
        )
        self._key_entry.pack(side="left", ipady=4)

        tk.Button(
            key_frame, text="👁", bg=p["BG"], fg=p["FG"], relief="flat",
            cursor="hand2", command=self._toggle_key,
        ).pack(side="left", padx=(4, 0))

        self._key_error = tk.Label(self, text="", bg=p["BG"], fg=p["RED"], font=FONT_SM)
        self._key_error.pack(anchor="w", padx=PAD)

        # ── Sliders ───────────────────────────────────────────────────────────
        self._interval_var = tk.IntVar(value=self._settings.refresh_interval)
        self._warning_var  = tk.IntVar(value=int(self._settings.month_warning_usd))
        self._critical_var = tk.IntVar(value=int(self._settings.month_critical_usd))

        self._slider_row("Refresh interval (s)", self._interval_var, from_=60, to=3600)
        self._slider_row("Warning threshold ($)", self._warning_var,  from_=1,  to=500)
        self._slider_row("Critical threshold ($)", self._critical_var, from_=1,  to=1000)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=p["BG"])
        btn_frame.pack(fill="x", padx=PAD, pady=PAD)

        tk.Button(
            btn_frame, text="Cancel", command=self.destroy,
            bg=p["BG_SEC"], fg=p["FG"], relief="flat", padx=12, pady=4,
        ).pack(side="right", padx=(4, 0))

        tk.Button(
            btn_frame, text="Save", command=self._save,
            bg=p["BLUE"], fg="#ffffff", relief="flat", padx=12, pady=4,
        ).pack(side="right")

    def _slider_row(self, label: str, var: tk.IntVar, from_: int, to: int) -> None:
        p = self._p
        frame = tk.Frame(self, bg=p["BG"])
        frame.pack(fill="x", padx=16, pady=4)
        tk.Label(frame, text=label, bg=p["BG"], fg=p["FG"],
                 font=FONT, width=24, anchor="w").pack(side="left")
        tk.Scale(
            frame, from_=from_, to=to, orient="horizontal", variable=var,
            bg=p["BG"], fg=p["FG"], highlightthickness=0, relief="flat",
        ).pack(side="left", fill="x", expand=True)

    def _toggle_key(self) -> None:
        self._show_key = not self._show_key
        self._key_entry.config(show="" if self._show_key else "●")

    def _save(self) -> None:
        key = self._key_var.get().strip()
        if not key:
            self._key_error.config(text="API key cannot be empty.")
            return
        self._key_error.config(text="")
        new_settings = Settings(
            api_key=key,
            refresh_interval=self._interval_var.get(),
            month_warning_usd=float(self._warning_var.get()),
            month_critical_usd=float(self._critical_var.get()),
        )
        save_settings(new_settings)
        self._on_save(new_settings)
        self.destroy()
