import importlib
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest


def test_default_settings():
    from config import Settings
    s = Settings()
    assert s.api_key == ""
    assert s.refresh_interval == 300
    assert s.month_warning_usd == 50.0
    assert s.month_critical_usd == 100.0


def test_save_and_load_roundtrip(tmp_path):
    from config import Settings, load_settings, save_settings
    with patch("config.CONFIG_FILE", tmp_path / "settings.json"), \
         patch("config.CONFIG_DIR", tmp_path):
        s = Settings(api_key="sk-test", refresh_interval=120,
                     month_warning_usd=25.0, month_critical_usd=75.0)
        save_settings(s)
        loaded = load_settings()
    assert loaded.api_key == "sk-test"
    assert loaded.refresh_interval == 120


def test_load_missing_file_returns_defaults(tmp_path):
    from config import load_settings
    with patch("config.CONFIG_FILE", tmp_path / "nonexistent.json"):
        s = load_settings()
    assert s.api_key == ""
    assert s.refresh_interval == 300


def test_refresh_interval_clamped_to_3600(tmp_path):
    from config import load_settings
    raw = {"api_key": "", "refresh_interval": 9999,
           "month_warning_usd": 50.0, "month_critical_usd": 100.0}
    (tmp_path / "settings.json").write_text(json.dumps(raw))
    with patch("config.CONFIG_FILE", tmp_path / "settings.json"), \
         patch("config.CONFIG_DIR", tmp_path):
        s = load_settings()
    assert s.refresh_interval == 3600


def test_refresh_interval_clamped_to_60(tmp_path):
    from config import load_settings
    raw = {"api_key": "", "refresh_interval": 0,
           "month_warning_usd": 50.0, "month_critical_usd": 100.0}
    (tmp_path / "settings.json").write_text(json.dumps(raw))
    with patch("config.CONFIG_FILE", tmp_path / "settings.json"), \
         patch("config.CONFIG_DIR", tmp_path):
        s = load_settings()
    assert s.refresh_interval == 60


def test_config_path_uses_appdata(monkeypatch):
    monkeypatch.setenv("APPDATA", "C:\\Users\\test\\AppData\\Roaming")
    # Re-import to pick up fresh module-level constants
    import config
    importlib.reload(config)
    try:
        assert "OpenAIUsageTray" in str(config.CONFIG_DIR)
        assert "APPDATA" not in str(config.CONFIG_DIR)  # env var was expanded
    finally:
        importlib.reload(config)  # restore module state for subsequent tests
