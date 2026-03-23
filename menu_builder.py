"""Pure functions that build menu item strings from UsageData."""
from __future__ import annotations

from typing import Optional
from api import ModelUsage, UsageData


def format_tokens(n: int) -> str:
    if n == 0:
        return "0"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if n >= 1_000:
        return f"{n // 1_000}k"
    return str(n)


def build_title(
    data: UsageData,
    warning: float,
    critical: float,
    month_cost: float,
) -> str:
    cost_str = f"${data.today_cost:.2f}"
    if month_cost >= critical:
        return f"🔴 {cost_str}"
    if month_cost >= warning:
        return f"⚠ {cost_str}"
    return cost_str


def build_summary_lines(data: UsageData) -> tuple[str, str]:
    today_line = (
        f"Today:      ${data.today_cost:.2f}  |  "
        f"{format_tokens(data.today_input_tokens)} in / "
        f"{format_tokens(data.today_output_tokens)} out"
    )
    month_line = (
        f"This month: ${data.month_cost:.2f}  |  "
        f"{format_tokens(data.month_input_tokens)} in / "
        f"{format_tokens(data.month_output_tokens)} out"
    )
    return today_line, month_line


def build_model_line(m: ModelUsage) -> str:
    cost = f"${m.month_cost:.2f}" if m.month_cost is not None else "—"
    tokens = (
        f"{format_tokens(m.month_input_tokens)} / "
        f"{format_tokens(m.month_output_tokens)}"
    )
    return f"{m.model}:  {cost}  |  {tokens}"


def build_last_updated(data: UsageData) -> str:
    return f"Last updated: {data.fetched_at.strftime('%H:%M')} (local time)"
