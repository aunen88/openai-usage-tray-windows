# OpenAI Usage Tray (Windows)

A Windows system tray app that tracks your OpenAI API spending and token usage, broken down by model, for today and the current billing month.

## What it shows

- Today and this month's total cost (USD) and token counts (input/output)
- Per-model breakdown with cost and tokens for each model you've used
- Warning and critical indicators when monthly spend exceeds your thresholds
- Polls every 5 minutes by default (configurable from 2 to 60 minutes)

Per-model costs come from a hardcoded pricing table in `api.py`. Models not in the table show a dash instead. If OpenAI changes prices, update the `PRICING` dict.

Token counts use local midnight for "today". Cost totals use UTC midnight (API limitation). Near UTC midnight, the two may briefly cover different periods.

## Requirements

- Windows 10 or 11
- An [OpenAI Admin API key](https://platform.openai.com/api-keys) with Usage: Read permission

## Getting an API key

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Under Permissions, select Usage: Read
4. Copy the key (you only see it once)

## Installation

Download `OpenAIUsageTray.exe` from the [Releases](../../releases) page and run it. No install needed.

The app starts in the system tray. It shows "No API key" until you right-click the icon, open Settings, and save your key.

## Usage

Hover over the tray icon for a summary tooltip. Left-click or right-click to open the menu, which shows today's cost, this month's cost, and a per-model breakdown. From there you can refresh, open settings, or quit.

## Settings

| Setting | Default | Description |
|---|---|---|
| API Key | - | Your OpenAI Admin API key (usage.read scope) |
| Refresh interval | 300s | How often to poll (120-3600 seconds) |
| Warning threshold | $50 | Monthly spend that triggers a warning indicator |
| Critical threshold | $100 | Monthly spend that triggers a critical indicator |

Settings are saved to `%APPDATA%\OpenAIUsageTray\settings.json`.

## Logs

Logs go to `%APPDATA%\OpenAIUsageTray\app.log`. Check this file if the icon shows an error.

## Building from source

Requires Python 3.11+ and pip.

```bat
git clone https://github.com/aunen88/openai-usage-tray-windows
cd openai-usage-tray-windows
build.bat
```

Output: `dist\OpenAIUsageTray.exe`

To run without building:

```bat
pip install -r requirements.txt
python main.py
```

## Tests

```bat
pip install -r requirements.txt
pytest tests/
```

## Linting

```bat
ruff check .
ruff format .
```

## License

MIT
