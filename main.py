"""OpenAIUsageTray — Windows system tray app for OpenAI API usage tracking.

Architecture
------------
• main thread  : hidden tkinter root + event loop (all GUI mutations here)
• pystray      : runs detached via icon.run_detached()
• polling      : daemon thread, posts results to GUI queue
• GUI queue    : queue.Queue drained by root.after(50ms)
"""
from __future__ import annotations

import logging
import os
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Optional

import pystray

from api import AuthError, RateLimitError, UsageData, fetch_usage
from config import Settings, load_settings
from icon_renderer import render_icon
from menu_builder import (
    build_last_updated, build_model_line, build_summary_lines, build_title,
)
from popup import DetailWindow, SettingsWindow

# ── Logging ──────────────────────────────────────────────────────────────────

_LOG_DIR = Path(os.environ.get("APPDATA", "~")) / "OpenAIUsageTray"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────


class App:
    """Owns all state. All public methods must be called on the main thread."""

    def __init__(self) -> None:
        self.settings: Settings = load_settings()
        self.usage: Optional[UsageData] = None
        self.status: str = "no_key" if not self.settings.api_key else "loading"

        # Backoff state (main-thread only after init)
        self._backoff_s: int = 60
        self._backoff_pending: bool = False
        self._backoff_after_id: Optional[str] = None

        # Settings window reference
        self._settings_win: Optional[tk.Toplevel] = None
        self._detail_win: Optional[tk.Toplevel] = None

        # Cross-thread dispatch queue
        self._gui_q: queue.Queue = queue.Queue()

        # Hidden tkinter root
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("OpenAIUsageTray")

        # Tray icon
        placeholder = render_icon(
            0.0,
            warning=self.settings.month_warning_usd,
            critical=self.settings.month_critical_usd,
        )
        self.icon = pystray.Icon(
            "OpenAIUsageTray",
            icon=placeholder,
            title="OpenAI Usage",
            menu=self._make_menu(),
        )

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self) -> None:
        self.root.after(50, self._drain_queue)
        self.root.after(100, self._initial_fetch)
        self.icon.run_detached()
        self.root.mainloop()

    # ── Queue ─────────────────────────────────────────────────────────────────

    def _post(self, fn, *args) -> None:
        self._gui_q.put((fn, args))

    def _drain_queue(self) -> None:
        try:
            while True:
                fn, args = self._gui_q.get_nowait()
                try:
                    fn(*args)
                except Exception:
                    log.exception("GUI queue callback raised")
        except queue.Empty:
            pass
        self.root.after(50, self._drain_queue)

    # ── Polling ───────────────────────────────────────────────────────────────

    def _initial_fetch(self) -> None:
        if self.settings.api_key:
            threading.Thread(target=self._fetch, daemon=True).start()
        self._schedule_next_poll()

    def _schedule_next_poll(self) -> None:
        self.root.after(self.settings.refresh_interval * 1000, self._poll_tick)

    def _poll_tick(self) -> None:
        """Main-thread timer — spawns fetch if not in backoff and interval elapsed."""
        if not self._backoff_pending and self.status != "ratelimit":
            if self.usage is None or (
                (datetime.now() - self.usage.fetched_at).total_seconds()
                >= self.settings.refresh_interval
            ):
                threading.Thread(target=self._fetch, daemon=True).start()
        self._schedule_next_poll()

    # ── Fetch (background thread) ─────────────────────────────────────────────

    def _fetch(self) -> None:
        if not self.settings.api_key:
            self._post(self._apply_state, "no_key", None)
            return
        try:
            data = fetch_usage(self.settings.api_key)
            self._backoff_s = 60
            log.info("Fetched: today=$%.2f month=$%.2f", data.today_cost, data.month_cost)
            self._post(self._apply_state, "ok", data)
        except AuthError as exc:
            log.warning("Auth error: %s", exc)
            self._backoff_s = 300  # back off 5 min on auth errors
            self._post(self._apply_state, "error", None)
            self._post(self._schedule_backoff)
        except RateLimitError as exc:
            self._backoff_s = (
                min(exc.retry_after, 3600) if exc.retry_after > 0
                else min(self._backoff_s * 2, 3600)
            )
            log.warning("Rate limited — backing off %ds", self._backoff_s)
            self._post(self._apply_state, "ratelimit", None)
        except Exception as exc:
            log.error("Fetch failed: %s", exc)
            self._post(self._apply_state, "stale" if self.usage else "error", None)

    # ── State application (main thread) ──────────────────────────────────────

    def _apply_state(self, status: str, data: Optional[UsageData]) -> None:
        self.status = status
        if data is not None:
            self.usage = data
        if status == "ratelimit":
            self._schedule_backoff()
        elif status == "ok":
            self._backoff_pending = False
        self._refresh_icon()
        self.icon.menu = self._make_menu()

    def _schedule_backoff(self) -> None:
        """Schedule a post-backoff retry. Silently drops duplicates (main thread)."""
        if self._backoff_pending:
            log.debug("Backoff already scheduled — skipping duplicate")
            return
        self._backoff_pending = True
        self._backoff_after_id = self.root.after(self._backoff_s * 1000, self._run_backoff)

    def _cancel_backoff(self) -> None:
        """Cancel any pending backoff timer (main thread)."""
        if self._backoff_after_id is not None:
            self.root.after_cancel(self._backoff_after_id)
            self._backoff_after_id = None
        self._backoff_pending = False

    def _run_backoff(self) -> None:
        self._backoff_pending = False
        self._backoff_after_id = None
        if self.settings.api_key:
            threading.Thread(target=self._fetch, daemon=True).start()

    # ── Icon + menu ───────────────────────────────────────────────────────────

    def _refresh_icon(self) -> None:
        today_cost = self.usage.today_cost if self.usage else 0.0
        img = render_icon(
            today_cost,
            warning=self.settings.month_warning_usd,
            critical=self.settings.month_critical_usd,
        )
        self.icon.icon = img
        # Update tray tooltip / title
        if self.usage:
            self.icon.title = build_title(
                self.usage,
                warning=self.settings.month_warning_usd,
                critical=self.settings.month_critical_usd,
                month_cost=self.usage.month_cost,
            )
        elif self.status == "no_key":
            self.icon.title = "OpenAI Usage — no key"
        elif self.status == "loading":
            self.icon.title = "OpenAI Usage — loading…"
        else:
            self.icon.title = "OpenAI Usage — error"

    def _make_menu(self) -> pystray.Menu:
        items: list = [
            pystray.MenuItem("Show Details",
                             lambda _i, _it: self._post(self._open_detail),
                             default=True),
            pystray.Menu.SEPARATOR,
        ]

        if self.usage and self.status in ("ok", "stale", "ratelimit"):
            today_line, month_line = build_summary_lines(self.usage)
            items += [
                pystray.MenuItem(today_line, None, enabled=False),
                pystray.MenuItem(month_line, None, enabled=False),
                pystray.Menu.SEPARATOR,
            ]
            for m in self.usage.models:
                items.append(pystray.MenuItem(build_model_line(m), None, enabled=False))
            items.append(pystray.Menu.SEPARATOR)
            if self.status == "stale":
                items.append(pystray.MenuItem("Network error — retrying…", None, enabled=False))
            elif self.status == "ratelimit":
                items.append(pystray.MenuItem(
                    f"Rate limited, retrying in {self._backoff_s}s…", None, enabled=False,
                ))
            else:
                items.append(pystray.MenuItem(build_last_updated(self.usage), None, enabled=False))
        elif self.status == "no_key":
            items.append(pystray.MenuItem("No API key — open Settings", None, enabled=False))
        elif self.status == "error":
            items.append(pystray.MenuItem("API error — check Settings", None, enabled=False))
        else:
            items.append(pystray.MenuItem("Loading…", None, enabled=False))

        items += [
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Refresh", lambda _i, _it: self._post(self._do_refresh)),
            pystray.MenuItem("Settings…", lambda _i, _it: self._post(self._open_settings)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda _i, _it: self._post(self._do_quit)),
        ]
        return pystray.Menu(*items)

    # ── UI actions (main thread) ──────────────────────────────────────────────

    def _do_refresh(self) -> None:
        """Bypass _backoff_pending — spawns fetch immediately (claude_tray pattern)."""
        self._cancel_backoff()
        threading.Thread(target=self._fetch, daemon=True).start()

    def _open_settings(self) -> None:
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.lift()
            return
        self._settings_win = SettingsWindow(self.root, self.settings, self._on_settings_saved)

    def _open_detail(self) -> None:
        if self._detail_win and self._detail_win.winfo_exists():
            self._detail_win.lift()
            return
        self._detail_win = DetailWindow(
            self.root,
            self.usage,
            self.usage.fetched_at if self.usage else None,
            self.settings,
            status=self.status,
            on_refresh=self._do_refresh,
            on_open_settings=self._open_settings,
        )

    def _on_settings_saved(self, new_settings: Settings) -> None:
        self.settings = new_settings
        self._cancel_backoff()
        self._backoff_s = 60
        if new_settings.api_key:
            self.status = "loading"
            self._refresh_icon()
            self.icon.menu = self._make_menu()
            threading.Thread(target=self._fetch, daemon=True).start()

    def _do_quit(self) -> None:
        self.icon.stop()
        self.root.destroy()


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
