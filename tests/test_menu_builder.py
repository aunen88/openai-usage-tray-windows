import pytest
from datetime import datetime

def _make_data(today_cost=4.20, month_cost=31.50,
               today_in=2_100_000, today_out=800_000,
               month_in=18_000_000, month_out=6_000_000):
    from api import UsageData, ModelUsage
    models = [
        ModelUsage("gpt-4o", 1_800_000, 600_000, 15_000_000, 5_000_000,
                   today_cost=3.10, month_cost=27.50),
        ModelUsage("gpt-4o-mini", 300_000, 200_000, 3_000_000, 1_000_000,
                   today_cost=1.10, month_cost=4.00),
        ModelUsage("o3-mini", 12_000, 4_000, 100_000, 40_000,
                   today_cost=None, month_cost=None),
    ]
    return UsageData(
        models=models,
        today_cost=today_cost, month_cost=month_cost,
        today_input_tokens=today_in, today_output_tokens=today_out,
        month_input_tokens=month_in, month_output_tokens=month_out,
        fetched_at=datetime(2026, 3, 21, 22, 34, 0),
    )

def test_format_tokens_k():
    from menu_builder import format_tokens
    assert format_tokens(12_000) == "12k"

def test_format_tokens_m():
    from menu_builder import format_tokens
    assert format_tokens(2_100_000) == "2.1M"

def test_format_tokens_m_round():
    from menu_builder import format_tokens
    assert format_tokens(2_000_000) == "2M"

def test_format_tokens_zero():
    from menu_builder import format_tokens
    assert format_tokens(0) == "0"

def test_title_normal():
    from menu_builder import build_title
    data = _make_data(today_cost=4.20)
    assert build_title(data, warning=50.0, critical=100.0, month_cost=31.50) == "$4.20"

def test_title_warning():
    from menu_builder import build_title
    data = _make_data(today_cost=4.20)
    assert build_title(data, warning=50.0, critical=100.0, month_cost=55.0).startswith("⚠")

def test_title_critical():
    from menu_builder import build_title
    data = _make_data(today_cost=4.20)
    assert build_title(data, warning=50.0, critical=100.0, month_cost=105.0).startswith("🔴")

def test_summary_lines():
    from menu_builder import build_summary_lines
    data = _make_data()
    today_line, month_line = build_summary_lines(data)
    assert "$4.20" in today_line
    assert "2.1M" in today_line
    assert "$31.50" in month_line

def test_model_line_known_cost():
    from menu_builder import build_model_line
    from api import ModelUsage
    m = ModelUsage("gpt-4o", 1_800_000, 600_000, 15_000_000, 5_000_000,
                   today_cost=3.10, month_cost=27.50)
    line = build_model_line(m)
    assert "gpt-4o" in line
    assert "$27.50" in line

def test_model_line_unknown_cost():
    from menu_builder import build_model_line
    from api import ModelUsage
    m = ModelUsage("o3-mini", 12_000, 4_000, 100_000, 40_000,
                   today_cost=None, month_cost=None)
    line = build_model_line(m)
    assert "—" in line

def test_last_updated_line():
    from menu_builder import build_last_updated
    data = _make_data()
    line = build_last_updated(data)
    assert "22:34" in line
