r"""Load/save settings to %APPDATA%\OpenAIUsageTray\settings.json."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger(__name__)

CONFIG_DIR = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "OpenAIUsageTray"
CONFIG_FILE = CONFIG_DIR / "settings.json"


@dataclass
class Settings:
    api_key: str = ""
    refresh_interval: int = 300       # seconds, 60–3600
    month_warning_usd: float = 50.0
    month_critical_usd: float = 100.0


def load_settings() -> Settings:
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            valid = {k: v for k, v in raw.items() if k in Settings.__dataclass_fields__}
            s = Settings(**valid)
            s.refresh_interval = max(60, min(s.refresh_interval, 3600))
            return s
        except Exception:
            log.warning("Could not load settings, using defaults.")
    return Settings()


def save_settings(settings: Settings) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
