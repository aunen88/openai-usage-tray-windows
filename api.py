"""OpenAI organization usage API — dataclasses, pricing, and HTTP calls."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests

log = logging.getLogger(__name__)

_TIMEOUT = 10
_COMPLETIONS_URL = "https://api.openai.com/v1/organization/usage/completions"
_COSTS_URL = "https://api.openai.com/v1/organization/costs"

# ---------------------------------------------------------------------------
# Pricing table — USD per 1M tokens (input, output)
# Update this dict when OpenAI changes prices.
# ---------------------------------------------------------------------------
PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o":               (2.50,  10.00),
    "gpt-4o-2024-11-20":    (2.50,  10.00),
    "gpt-4o-2024-08-06":    (2.50,  10.00),
    "gpt-4o-mini":          (0.15,   0.60),
    "gpt-4o-mini-2024-07-18": (0.15, 0.60),
    "o1":                   (15.00, 60.00),
    "o1-2024-12-17":        (15.00, 60.00),
    "o1-mini":              (1.10,   4.40),
    "o3-mini":              (1.10,   4.40),
    "gpt-4-turbo":          (10.00, 30.00),
    "gpt-4-turbo-2024-04-09": (10.00, 30.00),
    "gpt-4":                (30.00, 60.00),
    "gpt-3.5-turbo":        (0.50,   1.50),
    "gpt-3.5-turbo-0125":   (0.50,   1.50),
}


def compute_model_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Optional[float]:
    """Return dollar cost for the given token counts, or None if model unknown."""
    pricing = PRICING.get(model)
    if pricing is None:
        return None
    price_in, price_out = pricing
    return (input_tokens / 1_000_000) * price_in + (output_tokens / 1_000_000) * price_out


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ModelUsage:
    model: str
    input_tokens: int               # today
    output_tokens: int              # today
    month_input_tokens: int
    month_output_tokens: int
    today_cost: Optional[float]     # None if model not in PRICING
    month_cost: Optional[float]


@dataclass
class UsageData:
    models: list[ModelUsage]        # sorted by month_cost desc, then name
    today_cost: float               # org-level USD from costs endpoint
    month_cost: float               # org-level USD from costs endpoint
    today_input_tokens: int
    today_output_tokens: int
    month_input_tokens: int
    month_output_tokens: int
    fetched_at: datetime            # local time


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AuthError(Exception):
    """401 — API key rejected."""


class RateLimitError(Exception):
    """429 — rate limited."""
    def __init__(self, msg: str, retry_after: int = 300):
        super().__init__(msg)
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def fetch_completions(
    api_key: str,
    start_time: int,
    end_time: int,
) -> dict[str, tuple[int, int]]:
    """Return {model: (input_tokens, output_tokens)} summed across all pages."""
    headers = {"Authorization": f"Bearer {api_key}"}
    totals: dict[str, list[int]] = {}
    params: dict = {
        "start_time": start_time,
        "end_time": end_time,
        "group_by[]": "model",
        "limit": 100,
    }

    while True:
        resp = requests.get(_COMPLETIONS_URL, headers=headers, params=params, timeout=_TIMEOUT)
        if resp.status_code == 401:
            raise AuthError("HTTP 401 — API key rejected.")
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("retry-after", 300))
            raise RateLimitError(f"Rate limited — retry in {retry_after}s.", retry_after)
        resp.raise_for_status()

        body = resp.json()
        for bucket in body.get("data", []):
            model = bucket["model"]
            inp = bucket.get("input_tokens", 0)
            out = bucket.get("output_tokens", 0)
            if model not in totals:
                totals[model] = [0, 0]
            totals[model][0] += inp
            totals[model][1] += out

        if not body.get("has_more"):
            break
        params["page"] = body["next_page"]

    return {m: (v[0], v[1]) for m, v in totals.items()}


def fetch_costs(
    api_key: str,
    month_start: int,
    today_utc_start: int,
) -> tuple[float, float]:
    """Return (month_total_usd, today_usd).

    month_start: Unix timestamp of UTC midnight on the 1st of the billing month.
    today_utc_start: Unix timestamp of UTC midnight today (UTC).
    """
    from datetime import date, timezone

    headers = {"Authorization": f"Bearer {api_key}"}
    today_utc = datetime.fromtimestamp(today_utc_start, tz=timezone.utc).date()

    # Number of days elapsed in the billing month (minimum 1)
    days_elapsed = max(1, (today_utc - datetime.fromtimestamp(month_start, tz=timezone.utc).date()).days + 1)

    params = {
        "start_time": month_start,
        "bucket_width": "1d",
        "limit": days_elapsed,
    }

    resp = requests.get(_COSTS_URL, headers=headers, params=params, timeout=_TIMEOUT)
    if resp.status_code == 401:
        raise AuthError("HTTP 401 — API key rejected.")
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("retry-after", 300))
        raise RateLimitError(f"Rate limited — retry in {retry_after}s.", retry_after)
    resp.raise_for_status()

    body = resp.json()
    month_total = 0.0
    today_cost = 0.0

    for bucket in body.get("data", []):
        for result in bucket.get("results", []):
            value = float(result.get("amount", {}).get("value", 0.0))
            month_total += value
            bucket_date = datetime.fromtimestamp(bucket["start_time"], tz=timezone.utc).date()
            if bucket_date == today_utc:
                today_cost += value

    return month_total, today_cost


def fetch_usage(api_key: str) -> UsageData:
    """Fire all three API calls concurrently and return merged UsageData."""
    import concurrent.futures
    from datetime import date, timezone
    import time

    now = datetime.now()
    local_midnight = datetime(now.year, now.month, now.day)
    month_start_local = datetime(now.year, now.month, 1)

    today_utc = date.today()
    month_start_utc = date(today_utc.year, today_utc.month, 1)
    month_start_unix = int(datetime(
        month_start_utc.year, month_start_utc.month, 1,
        tzinfo=timezone.utc
    ).timestamp())
    today_utc_start = int(datetime(
        today_utc.year, today_utc.month, today_utc.day,
        tzinfo=timezone.utc
    ).timestamp())

    now_unix = int(time.time())
    local_midnight_unix = int(local_midnight.timestamp())
    month_start_local_unix = int(month_start_local.timestamp())

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        f_today = ex.submit(fetch_completions, api_key, local_midnight_unix, now_unix)
        f_month = ex.submit(fetch_completions, api_key, month_start_local_unix, now_unix)
        f_costs = ex.submit(fetch_costs, api_key, month_start_unix, today_utc_start)

        today_tokens = f_today.result()
        month_tokens = f_month.result()
        month_cost, today_cost_val = f_costs.result()

    all_models = set(today_tokens) | set(month_tokens)

    model_list: list[ModelUsage] = []
    for model in all_models:
        ti, to = today_tokens.get(model, (0, 0))
        mi, mo = month_tokens.get(model, (0, 0))
        model_list.append(ModelUsage(
            model=model,
            input_tokens=ti,
            output_tokens=to,
            month_input_tokens=mi,
            month_output_tokens=mo,
            today_cost=compute_model_cost(model, ti, to),
            month_cost=compute_model_cost(model, mi, mo),
        ))

    model_list.sort(key=lambda m: (-(m.month_cost or 0.0), m.model))

    return UsageData(
        models=model_list,
        today_cost=today_cost_val,
        month_cost=month_cost,
        today_input_tokens=sum(t[0] for t in today_tokens.values()),
        today_output_tokens=sum(t[1] for t in today_tokens.values()),
        month_input_tokens=sum(t[0] for t in month_tokens.values()),
        month_output_tokens=sum(t[1] for t in month_tokens.values()),
        fetched_at=datetime.now(),
    )
