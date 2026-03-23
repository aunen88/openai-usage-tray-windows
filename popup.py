"""Tkinter popup windows for OpenAI Usage Tray — modern dark-glass design.

DetailWindow   – borderless flyout, slides up from taskbar
SettingsWindow – modal settings sheet, centered
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

import win32_ui
from api import UsageData
from config import Settings, save_settings

# ── Palette ───────────────────────────────────────────────────────────────────

def _palette() -> dict:
    light = win32_ui.is_light_theme()
    if light:
        return {
            "BG":          "#f5f4f0",
            "BG_CARD":     "#eceae4",
            "BG_HOVER":    "#e0deda",
            "FG":          "#1a1a18",
            "FG_DIM":      "#666660",
            "FG_MUTED":    "#9a9990",
            "DIVIDER":     "#d5d3cc",
            "ACCENT":      "#22a84a",
            "GREEN":       "#22a84a",
            "ORANGE":      "#d97a1a",
            "RED":         "#c42b20",
            "BTN_BG":      "#e4e2dc",
            "BTN_FG":      "#1a1a18",
            "ACRYLIC":     0xF0F0EEE8,
            "BANNER_WARN": "#fff5e6",
        }
    return {
        "BG":          "#161618",
        "BG_CARD":     "#1e1e22",
        "BG_HOVER":    "#252529",
        "FG":          "#f0efe8",
        "FG_DIM":      "#888882",
        "FG_MUTED":    "#555550",
        "DIVIDER":     "#2c2c30",
        "ACCENT":      "#4ade80",
        "GREEN":       "#4ade80",
        "ORANGE":      "#fb923c",
        "RED":         "#f87171",
        "BTN_BG":      "#26262a",
        "BTN_FG":      "#c8c7c0",
        "ACRYLIC":     0xF0181618,
        "BANNER_WARN": "#2a1a0a",
    }

# ── Typography ────────────────────────────────────────────────────────────────

_FONT_BODY   = ("Segoe UI Variable", 10)
_FONT_BODY_B = ("Segoe UI Variable", 10, "bold")
_FONT_LABEL  = ("Segoe UI Variable", 9)
_FONT_NUM    = ("Consolas", 18, "bold")
_FONT_NUM_SM = ("Consolas", 11)
_FONT_TS     = ("Consolas", 9)

# ── Constants ─────────────────────────────────────────────────────────────────

_WIN_W       = 300
_SLIDE_PX    = 160
_SLIDE_MS    = 150
_SLIDE_STEPS = 12
_FADE_MS     = 100
_FADE_STEPS  = 8
_BAR_H       = 4
_BAR_ANIM_MS = 350
_BAR_STEPS   = 18

# ── Helpers ───────────────────────────────────────────────────────────────────

def _cost_color(cost: float, warn: float, crit: float, pal: dict) -> str:
    return pal["RED"] if cost >= crit else pal["ORANGE"] if cost >= warn else pal["GREEN"]


def _rounded_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int,
                  r: int, **kw) -> None:
    canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90,  extent=90,  style="pieslice", **kw)
    canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0,   extent=90,  style="pieslice", **kw)
    canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90,  style="pieslice", **kw)
    canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90,  style="pieslice", **kw)
    canvas.create_rectangle(x1+r, y1, x2-r, y2, **kw)
    canvas.create_rectangle(x1, y1+r, x2, y2-r, **kw)


def _draw_brand_icon(canvas: tk.Canvas, size: int, color: str) -> None:
    """Green rounded-square with a simple circle mark."""
    r = size // 5
    _rounded_rect(canvas, 0, 0, size, size, r, fill=color, outline="")
    m = size // 5
    canvas.create_oval(m, m, size-m, size-m, outline="white", width=1.5)
    canvas.create_arc(m, m, size-m, size-m, start=45, extent=180,
                      fill=color, outline=color, style="pieslice")


# ── Detail window ─────────────────────────────────────────────────────────────

class DetailWindow(tk.Toplevel):
    """Modern dark-glass flyout showing OpenAI cost data."""

    def __init__(
        self,
        root: tk.Tk,
        usage: Optional[UsageData],
        last_updated,
        settings: Settings,
        *,
        status: str = "ok",
        on_refresh: Callable,
        on_open_settings: Callable,
    ):
        super().__init__(root)
        self._root             = root
        self._on_refresh       = on_refresh
        self._on_open_settings = on_open_settings
        self._settings         = settings
        self._status           = status
        self._closing          = False
        self._bar_canvases: list[tuple[tk.Canvas, float]] = []

        self._pal = _palette()

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        self._build(usage, last_updated)
        self.after(0, self._init_win32)
        self.bind("<Escape>", lambda _e: self.close())
        self.bind("<FocusOut>", self._on_focus_out)

    def _init_win32(self) -> None:
        self.update_idletasks()
        hwnd = self.winfo_id()
        win32_ui.apply_rounded_corners(hwnd)
        ok = win32_ui.apply_acrylic(hwnd, tint_color=self._pal["ACRYLIC"])
        if not ok:
            self.configure(bg=self._pal["BG"])
        self._position_and_animate()

    def _build(self, usage, last_updated) -> None:
        p = self._pal
        outer = tk.Frame(self, bg=p["BG"], bd=0)
        outer.pack(fill="both", expand=True, padx=1, pady=1)
        self._build_header(outer)
        tk.Frame(outer, bg=p["DIVIDER"], height=1).pack(fill="x")
        self._build_body(outer, usage)
        tk.Frame(outer, bg=p["DIVIDER"], height=1).pack(fill="x")
        self._build_footer(outer, last_updated)

    def _build_header(self, parent: tk.Widget) -> None:
        p = self._pal
        row = tk.Frame(parent, bg=p["BG"])
        row.pack(fill="x", padx=14, pady=(13, 11))

        ic = tk.Canvas(row, width=28, height=28, bg=p["BG"], highlightthickness=0)
        ic.pack(side="left")
        _draw_brand_icon(ic, 28, p["ACCENT"])

        txt = tk.Frame(row, bg=p["BG"])
        txt.pack(side="left", padx=(9, 0))
        tk.Label(txt, text="OpenAI Usage", bg=p["BG"], fg=p["FG"],
                 font=_FONT_BODY_B).pack(anchor="w")
        tk.Label(txt, text="Organization costs", bg=p["BG"], fg=p["FG_DIM"],
                 font=_FONT_LABEL).pack(anchor="w")

        dot_color = {
            "ok":         p["GREEN"],
            "stale":      p["ORANGE"],
            "ratelimit":  p["ORANGE"],
            "error":      p["RED"],
            "auth_error": p["RED"],
        }.get(self._status, p["FG_MUTED"])
        dot = tk.Canvas(row, width=9, height=9, bg=p["BG"], highlightthickness=0)
        dot.pack(side="right", padx=(0, 2))
        dot.create_oval(1, 1, 8, 8, fill=dot_color, outline="")

    def _build_body(self, parent: tk.Widget, usage) -> None:
        p    = self._pal
        warn = self._settings.month_warning_usd
        crit = self._settings.month_critical_usd

        wrap = tk.Frame(parent, bg=p["BG"])
        wrap.pack(fill="x", padx=10, pady=10)

        if usage is None:
            msg = {
                "error":      "Could not reach API — check connection",
                "auth_error": "Invalid API key — open Settings",
                "ratelimit":  "Rate limited — will retry shortly",
                "stale":      "Showing cached data — retrying…",
                "no_key":     "No API key — open Settings",
            }.get(self._status, "Fetching data…")
            tk.Label(wrap, text=msg, bg=p["BG"], fg=p["FG_DIM"],
                     font=_FONT_LABEL, wraplength=260, justify="left",
                     ).pack(padx=4, pady=6, anchor="w")
        else:
            self._cost_card(wrap, "Today", usage.today_cost, warn, crit)
            self._cost_card(wrap, "Month", usage.month_cost, warn, crit,
                            show_bar=True, bar_max=crit)
            top = [m for m in usage.models if m.month_cost is not None][:4]
            if top:
                tk.Frame(wrap, bg=p["DIVIDER"], height=1).pack(fill="x", pady=(4, 0))
                for m in top:
                    self._model_row(wrap, m)

        if self._status == "ratelimit":
            banner_bg = p["BANNER_WARN"]
            banner = tk.Frame(wrap, bg=banner_bg)
            banner.pack(fill="x", pady=(4, 0))
            tk.Frame(banner, bg=p["ORANGE"], height=1).pack(fill="x")
            tk.Label(banner, text="⚠  Rate limited — retrying…",
                     bg=banner_bg, fg=p["ORANGE"],
                     font=_FONT_LABEL, anchor="w",
                     ).pack(fill="x", padx=10, pady=7)

    def _cost_card(self, parent: tk.Widget, label: str, cost: float,
                   warn: float, crit: float, show_bar: bool = False,
                   bar_max: float = 1.0) -> None:
        p   = self._pal
        clr = _cost_color(cost, warn, crit, p)

        card = tk.Frame(parent, bg=p["BG_CARD"],
                        highlightthickness=1,
                        highlightbackground=p["DIVIDER"])
        card.pack(fill="x", pady=3)

        top = tk.Frame(card, bg=p["BG_CARD"])
        top.pack(fill="x", padx=12, pady=(9, 5 if show_bar else 9))

        tk.Label(top, text=label, bg=p["BG_CARD"], fg=p["FG_DIM"],
                 font=_FONT_LABEL).pack(side="left")
        tk.Label(top, text=f"${cost:.2f}", bg=p["BG_CARD"], fg=clr,
                 font=_FONT_NUM).pack(side="right")

        if show_bar and bar_max > 0:
            bar_frame = tk.Frame(card, bg=p["BG_CARD"])
            bar_frame.pack(fill="x", padx=12, pady=(0, 9))
            canvas = tk.Canvas(bar_frame, height=_BAR_H, bg=p["BG_CARD"],
                               highlightthickness=0)
            canvas.pack(fill="x")
            fill_ratio = min(cost / bar_max, 1.0)

            def _on_configure(event, cv=canvas, ratio=fill_ratio, color=clr):
                tw = event.width
                cv.delete("all")
                _rounded_rect(cv, 0, 0, tw, _BAR_H, _BAR_H // 2,
                              fill=p["DIVIDER"], outline="")
                cv._target_fill = int(tw * ratio)
                cv._fill_color  = color
                cv._track_w     = tw

            canvas.bind("<Configure>", _on_configure)
            self._bar_canvases.append((canvas, fill_ratio))

    def _model_row(self, parent: tk.Widget, model) -> None:
        p = self._pal
        row = tk.Frame(parent, bg=p["BG"])
        row.pack(fill="x", pady=1)
        name = model.model
        if len(name) > 22:
            name = name[:20] + "…"
        tk.Label(row, text=name, bg=p["BG"], fg=p["FG_DIM"],
                 font=_FONT_LABEL).pack(side="left", padx=4)
        cost_str = f"${model.month_cost:.2f}" if model.month_cost is not None else "—"
        tk.Label(row, text=cost_str, bg=p["BG"], fg=p["FG"],
                 font=_FONT_NUM_SM).pack(side="right", padx=4)

    def _start_bar_animations(self) -> None:
        for canvas, fill_ratio in self._bar_canvases:
            self._anim_bar(canvas, fill_ratio, step=0)

    def _anim_bar(self, canvas: tk.Canvas, fill_ratio: float, step: int) -> None:
        if step > _BAR_STEPS:
            return
        p = self._pal
        try:
            tw = getattr(canvas, "_track_w", canvas.winfo_width())
            if tw < 2:
                try:
                    self.after(20, lambda: self._anim_bar(canvas, fill_ratio, step))
                except tk.TclError:
                    pass
                return
            color = getattr(canvas, "_fill_color", p["GREEN"])
            t     = step / _BAR_STEPS
            ease  = 1 - (1 - t) ** 3
            fw    = int(tw * fill_ratio * ease)
            canvas.delete("fill")
            if fw > 0:
                _rounded_rect(canvas, 0, 0, fw, _BAR_H, _BAR_H // 2,
                              fill=color, outline="", tags="fill")
        except tk.TclError:
            return
        self.after(max(1, _BAR_ANIM_MS // _BAR_STEPS),
                   lambda: self._anim_bar(canvas, fill_ratio, step + 1))

    def _build_footer(self, parent: tk.Widget, last_updated) -> None:
        p  = self._pal
        ts = last_updated.strftime("%H:%M:%S") if last_updated else "never"

        row = tk.Frame(parent, bg=p["BG"])
        row.pack(fill="x", padx=12, pady=8)

        tk.Label(row, text=f"updated {ts}", bg=p["BG"], fg=p["FG_MUTED"],
                 font=_FONT_TS).pack(side="left")

        btn_kw = dict(font=_FONT_LABEL, relief="flat", bd=0,
                      padx=10, pady=4, cursor="hand2")
        tk.Button(row, text="Settings", command=self._do_settings,
                  bg=p["BTN_BG"], fg=p["BTN_FG"],
                  activebackground=p["BG_HOVER"], activeforeground=p["FG"],
                  **btn_kw).pack(side="right")
        tk.Button(row, text="Refresh", command=self._do_refresh,
                  bg=p["BG_CARD"], fg=p["ACCENT"],
                  activebackground=p["BG_HOVER"], activeforeground=p["ACCENT"],
                  **btn_kw).pack(side="right", padx=(0, 6))

    def _position_and_animate(self) -> None:
        self.update_idletasks()
        sw  = self.winfo_screenwidth()
        sh  = self.winfo_screenheight()
        tb  = win32_ui.taskbar_height()
        w   = max(self.winfo_reqwidth(), _WIN_W)
        h   = max(self.winfo_reqheight(), self.winfo_height())
        x       = sw - w - 12
        y_end   = sh - h - tb - 12
        y_start = y_end + _SLIDE_PX
        self.geometry(f"{w}x{h}+{x}+{y_start}")
        self.attributes("-alpha", 1.0)
        self.lift()
        self.after(50, self.focus_force)
        self._animate_slide(x, y_start, y_end, step=0)

    def _animate_slide(self, x: int, y_from: int, y_to: int, step: int) -> None:
        if step >= _SLIDE_STEPS:
            try:
                self.geometry(f"+{x}+{y_to}")
                self._start_bar_animations()
            except tk.TclError:
                pass
            return
        t    = (step + 1) / _SLIDE_STEPS
        ease = 1 - (1 - t) ** 2
        y    = int(y_from + (y_to - y_from) * ease)
        try:
            self.geometry(f"+{x}+{y}")
        except tk.TclError:
            return
        self.after(max(1, _SLIDE_MS // _SLIDE_STEPS),
                   lambda: self._animate_slide(x, y_from, y_to, step + 1))

    def close(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._animate_fade(step=0)

    def _animate_fade(self, step: int) -> None:
        if step >= _FADE_STEPS:
            try:
                self.destroy()
            except tk.TclError:
                pass
            return
        alpha = 1.0 - (step + 1) / _FADE_STEPS
        try:
            self.attributes("-alpha", alpha)
        except tk.TclError:
            return
        self.after(max(1, _FADE_MS // _FADE_STEPS),
                   lambda: self._animate_fade(step + 1))

    def _on_focus_out(self, _event) -> None:
        self.after(50, self._check_focus)

    def _check_focus(self) -> None:
        if self._closing:
            return
        try:
            focused = self.focus_displayof()
        except tk.TclError:
            return
        if focused is None or not str(focused).startswith(str(self)):
            self.close()

    def _do_refresh(self) -> None:
        self.close()
        self._root.after(_FADE_MS + 20, self._on_refresh)

    def _do_settings(self) -> None:
        self.close()
        self._root.after(_FADE_MS + 20, self._on_open_settings)


# ── Settings window ───────────────────────────────────────────────────────────

class SettingsWindow(tk.Toplevel):
    """Settings flyout — dark-glass design, centered on screen."""

    def __init__(
        self,
        master: tk.Tk,
        settings: Settings,
        on_save: Callable[[Settings], None],
    ) -> None:
        super().__init__(master)
        self._settings = settings
        self._on_save  = on_save
        self._closing  = False
        self._pal      = _palette()

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        self._build()
        self.after(0, self._init_win32)
        self.bind("<Escape>", lambda _e: self.close())

    def _init_win32(self) -> None:
        try:
            self.update_idletasks()
            hwnd = self.winfo_id()
            win32_ui.apply_rounded_corners(hwnd)
            ok = win32_ui.apply_acrylic(hwnd, tint_color=self._pal["ACRYLIC"])
            if not ok:
                self.configure(bg=self._pal["BG"])
            self._center_and_show()
        except tk.TclError:
            pass

    def _build(self) -> None:
        p = self._pal
        outer = tk.Frame(self, bg=p["BG"])
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        # Header
        hdr = tk.Frame(outer, bg=p["BG"])
        hdr.pack(fill="x", padx=14, pady=(13, 11))
        ic = tk.Canvas(hdr, width=28, height=28, bg=p["BG"], highlightthickness=0)
        ic.pack(side="left")
        _draw_brand_icon(ic, 28, p["ACCENT"])
        txt = tk.Frame(hdr, bg=p["BG"])
        txt.pack(side="left", padx=(9, 0))
        tk.Label(txt, text="Settings", bg=p["BG"], fg=p["FG"],
                 font=_FONT_BODY_B).pack(anchor="w")
        tk.Label(txt, text="OpenAI Usage Tray", bg=p["BG"], fg=p["FG_DIM"],
                 font=_FONT_LABEL).pack(anchor="w")

        tk.Frame(outer, bg=p["DIVIDER"], height=1).pack(fill="x")

        body = tk.Frame(outer, bg=p["BG"])
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # API key field
        tk.Label(body, text="OpenAI Admin API Key", bg=p["BG"], fg=p["FG"],
                 font=_FONT_BODY).pack(anchor="w")
        key_row = tk.Frame(body, bg=p["BG"])
        key_row.pack(fill="x", pady=(4, 0))

        self._key_var = tk.StringVar(value=self._settings.api_key)
        self._key_entry = tk.Entry(
            key_row, textvariable=self._key_var, show="●",
            bg=p["BG_CARD"], fg=p["FG"], insertbackground=p["FG"],
            relief="flat", width=28, font=_FONT_LABEL,
            highlightthickness=1, highlightbackground=p["DIVIDER"],
        )
        self._key_entry.pack(side="left", ipady=5)

        self._show_key = False

        def _toggle_key():
            self._show_key = not self._show_key
            self._key_entry.config(show="" if self._show_key else "●")

        eye = tk.Label(key_row, text="👁", bg=p["BG"], fg=p["FG_DIM"],
                       font=("Segoe UI", 11), cursor="hand2")
        eye.pack(side="left", padx=(6, 0))
        eye.bind("<Button-1>", lambda _e: _toggle_key())

        self._key_error = tk.Label(body, text="", bg=p["BG"],
                                   fg=p["RED"], font=_FONT_LABEL)
        self._key_error.pack(anchor="w")

        tk.Frame(body, bg=p["DIVIDER"], height=1).pack(fill="x", pady=8)

        # Sliders
        self._interval_var = tk.IntVar(value=self._settings.refresh_interval)
        self._warning_var  = tk.IntVar(value=int(self._settings.month_warning_usd))
        self._critical_var = tk.IntVar(value=int(self._settings.month_critical_usd))

        self._slider_row(body, "Refresh interval", self._interval_var,
                         60, 3600, "s", p["ACCENT"])
        self._slider_row(body, "Warning threshold", self._warning_var,
                         1, 500, "$", p["ORANGE"])
        self._slider_row(body, "Critical threshold", self._critical_var,
                         1, 1000, "$", p["RED"])

        tk.Frame(outer, bg=p["DIVIDER"], height=1).pack(fill="x")
        ftr = tk.Frame(outer, bg=p["BG"])
        ftr.pack(fill="x", padx=14, pady=10)

        btn_kw = dict(font=_FONT_LABEL, relief="flat", bd=0,
                      padx=14, pady=5, cursor="hand2")
        tk.Button(ftr, text="Save", command=self._save,
                  bg=p["ACCENT"], fg="#ffffff",
                  activebackground=p["GREEN"], activeforeground="#ffffff",
                  **btn_kw).pack(side="right")
        tk.Button(ftr, text="Cancel", command=self.close,
                  bg=p["BTN_BG"], fg=p["BTN_FG"],
                  activebackground=p["BG_HOVER"], activeforeground=p["FG"],
                  **btn_kw).pack(side="right", padx=(0, 8))

    def _slider_row(self, parent: tk.Widget, label: str, var: tk.IntVar,
                    from_: int, to: int, unit: str, accent: str) -> None:
        p   = self._pal
        row = tk.Frame(parent, bg=p["BG"])
        row.pack(fill="x", pady=4)

        hdr = tk.Frame(row, bg=p["BG"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=label, bg=p["BG"], fg=p["FG"],
                 font=_FONT_BODY).pack(side="left")
        val_lbl = tk.Label(hdr, text=f"{var.get()}{unit}",
                           bg=p["BG"], fg=accent, font=_FONT_BODY)
        val_lbl.pack(side="right")

        def _on_move(v: str) -> None:
            val_lbl.config(text=f"{int(float(v))}{unit}")

        tk.Scale(
            row, from_=from_, to=to, orient="horizontal",
            variable=var, command=_on_move,
            bg=p["BG"], fg=p["FG"], troughcolor=p["BG_CARD"],
            highlightthickness=0, showvalue=False,
            relief="flat", sliderlength=16, bd=0,
        ).pack(fill="x")

    def _center_and_show(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = max(self.winfo_reqwidth(), 320)
        h  = max(self.winfo_reqheight(), self.winfo_height())
        self.geometry(f"{w}x{h}+{max(0,(sw-w)//2)}+{max(0,(sh-h)//2)}")
        self.attributes("-alpha", 1.0)
        self.lift()
        self.after(50, self.focus_force)

    def close(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.destroy()

    def _save(self) -> None:
        key = self._key_var.get().strip()
        if not key:
            self._key_error.config(text="API key cannot be empty.")
            return
        self._key_error.config(text="")
        new = Settings(
            api_key            = key,
            refresh_interval   = self._interval_var.get(),
            month_warning_usd  = float(self._warning_var.get()),
            month_critical_usd = float(self._critical_var.get()),
        )
        save_settings(new)
        self._on_save(new)
        self.close()
