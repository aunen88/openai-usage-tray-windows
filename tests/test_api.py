import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Task 3: Dataclasses and Pricing Table
# ---------------------------------------------------------------------------

def test_model_usage_defaults():
    from api import ModelUsage
    m = ModelUsage(model="gpt-4o", input_tokens=1_000_000, output_tokens=500_000,
                   month_input_tokens=5_000_000, month_output_tokens=2_000_000,
                   today_cost=None, month_cost=None)
    assert m.model == "gpt-4o"
    assert m.input_tokens == 1_000_000

def test_known_model_cost():
    from api import compute_model_cost, PRICING
    assert "gpt-4o" in PRICING
    cost = compute_model_cost("gpt-4o", input_tokens=1_000_000, output_tokens=500_000)
    # gpt-4o: $2.50/M in, $10.00/M out → $2.50 + $5.00 = $7.50
    assert abs(cost - 7.50) < 0.01

def test_unknown_model_cost_returns_none():
    from api import compute_model_cost
    assert compute_model_cost("gpt-unknown-9000", 100, 100) is None

def test_pricing_table_has_required_models():
    from api import PRICING
    for model in ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"]:
        assert model in PRICING, f"{model} missing from PRICING table"


# ---------------------------------------------------------------------------
# Task 4: Completions Endpoint
# ---------------------------------------------------------------------------

def _mock_response(body: dict, status: int = 200, headers: dict | None = None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body
    r.headers = headers or {}
    r.raise_for_status = MagicMock()
    return r

def test_fetch_completions_single_page():
    from api import fetch_completions
    page = {
        "data": [
            {"model": "gpt-4o",      "input_tokens": 1000, "output_tokens": 500,  "results": []},
            {"model": "gpt-4o-mini", "input_tokens": 2000, "output_tokens": 1000, "results": []},
        ],
        "has_more": False,
        "next_page": None,
    }
    with patch("api.requests.get", return_value=_mock_response(page)):
        result = fetch_completions("sk-test", start_time=0, end_time=1)
    assert result["gpt-4o"] == (1000, 500)
    assert result["gpt-4o-mini"] == (2000, 1000)

def test_fetch_completions_pagination():
    from api import fetch_completions
    page1 = {
        "data": [{"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "results": []}],
        "has_more": True,
        "next_page": "tok123",
    }
    page2 = {
        "data": [{"model": "gpt-4o", "input_tokens": 200, "output_tokens": 100, "results": []}],
        "has_more": False,
        "next_page": None,
    }
    responses = [_mock_response(page1), _mock_response(page2)]
    with patch("api.requests.get", side_effect=responses):
        result = fetch_completions("sk-test", start_time=0, end_time=1)
    assert result["gpt-4o"] == (300, 150)

def test_fetch_completions_401_raises_auth_error():
    from api import fetch_completions, AuthError
    with patch("api.requests.get", return_value=_mock_response({}, status=401)):
        with pytest.raises(AuthError):
            fetch_completions("bad-key", start_time=0, end_time=1)

def test_fetch_completions_429_raises_rate_limit():
    from api import fetch_completions, RateLimitError
    r = _mock_response({}, status=429, headers={"retry-after": "60"})
    with patch("api.requests.get", return_value=r):
        with pytest.raises(RateLimitError) as exc_info:
            fetch_completions("sk-test", start_time=0, end_time=1)
    assert exc_info.value.retry_after == 60


# ---------------------------------------------------------------------------
# Task 5: Costs Endpoint
# ---------------------------------------------------------------------------

def test_fetch_costs_sums_buckets():
    from api import fetch_costs
    body = {
        "data": [
            {"start_time": 1700000000, "results": [{"amount": {"value": 3.10, "currency": "usd"}}]},
            {"start_time": 1700086400, "results": [{"amount": {"value": 1.10, "currency": "usd"}}]},
        ],
        "has_more": False,
    }
    with patch("api.requests.get", return_value=_mock_response(body)):
        month_total, today_cost = fetch_costs("sk-test", month_start=0, today_utc_start=1700086400)
    assert abs(month_total - 4.20) < 0.001
    assert abs(today_cost - 1.10) < 0.001

def test_fetch_costs_today_bucket_absent_returns_zero():
    from api import fetch_costs
    body = {
        "data": [
            {"start_time": 1700000000, "results": [{"amount": {"value": 3.10, "currency": "usd"}}]},
        ],
        "has_more": False,
    }
    with patch("api.requests.get", return_value=_mock_response(body)):
        month_total, today_cost = fetch_costs("sk-test", month_start=0, today_utc_start=1700086400)
    assert abs(month_total - 3.10) < 0.001
    assert today_cost == 0.0

def test_fetch_costs_401_raises_auth_error():
    from api import fetch_costs, AuthError
    with patch("api.requests.get", return_value=_mock_response({}, status=401)):
        with pytest.raises(AuthError):
            fetch_costs("bad-key", month_start=0, today_utc_start=0)


# ---------------------------------------------------------------------------
# Task 6: Concurrent Fetch and Merge
# ---------------------------------------------------------------------------

def test_fetch_usage_merges_into_usage_data():
    from api import fetch_usage, UsageData

    completions_today = {"gpt-4o": (1_000_000, 500_000)}
    completions_month = {"gpt-4o": (5_000_000, 2_000_000)}
    costs = (31.50, 4.20)

    with patch("api.fetch_completions", side_effect=[completions_today, completions_month]), \
         patch("api.fetch_costs", return_value=costs):
        data = fetch_usage("sk-test")

    assert isinstance(data, UsageData)
    assert abs(data.today_cost - 4.20) < 0.001
    assert abs(data.month_cost - 31.50) < 0.001
    assert data.today_input_tokens == 1_000_000
    assert data.today_output_tokens == 500_000
    assert data.month_input_tokens == 5_000_000
    assert data.month_output_tokens == 2_000_000
    assert len(data.models) == 1
    m = data.models[0]
    assert m.model == "gpt-4o"
    assert m.input_tokens == 1_000_000
    assert m.month_input_tokens == 5_000_000
    # gpt-4o today cost: 1M * $2.50/M + 0.5M * $10/M = $2.50 + $5.00 = $7.50
    assert abs(m.today_cost - 7.50) < 0.01
