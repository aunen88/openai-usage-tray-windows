# OpenAI Usage Tray (Windows)

A Windows system tray app that shows your OpenAI API token usage and costs at a glance — per model, for today and the current billing month.

## What it shows

- **Today** and **this month** total cost (USD) and token counts (input / output)
- **Per-model breakdown**: cost and tokens for each model you've used
- Spend warning (⚠) and critical (🔴) indicators when monthly spend exceeds your thresholds
- Updates every 5 minutes (configurable)

> **Note:** Per-model costs are derived by multiplying your token counts by a hardcoded pricing table in `api.py`. Costs for models not in the table show `—`. Update the `PRICING` dict in `api.py` if OpenAI changes prices.

> **Timezone note:** Token counts use local midnight for the "today" window. Cost totals use UTC midnight (API limitation). Near UTC midnight, today's tokens and cost may briefly show different periods.

## Requirements

- Windows 10 or 11
- An [OpenAI Admin API key](https://platform.openai.com/api-keys) with **Usage: Read** permission

## Getting an Admin API key

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click **Create new secret key**
3. Under **Permissions**, select **Usage: Read**
4. Copy the key — you'll only see it once

## Installation

1. Download `OpenAIUsageTray.exe` from the [Releases](../../releases) page
2. Run it — no installation needed
3. Right-click the tray icon → **Settings…** to enter your API key

The app starts immediately in the system tray. It will show "No API key" until you open Settings and save a key.

## Usage

- **Hover** over the tray icon to see a summary tooltip
- **Left-click** or **right-click** the tray icon to open the menu
- The menu shows today's cost, this month's cost, and a per-model breakdown
- Select **Refresh** to fetch immediately, **Settings…** to change configuration, or **Quit** to exit

## Settings

| Setting | Default | Description |
|---|---|---|
| API Key | — | Your OpenAI Admin API key (`usage.read` scope) |
| Refresh interval | 300s | How often to poll (60–3600 seconds) |
| Warning threshold | $50 | Monthly spend that turns the icon ⚠ |
| Critical threshold | $100 | Monthly spend that turns the icon 🔴 |

Settings are saved to `%APPDATA%\OpenAIUsageTray\settings.json`.

## Logs

Application logs are written to `%APPDATA%\OpenAIUsageTray\app.log`. Check this file if the icon shows an error.

## Building from source

Requires Python 3.11+ and pip.

```bat
git clone <repo-url>
cd openai_usage_tray_windows
build.bat
```

The executable is written to `dist\OpenAIUsageTray.exe`.

To run from source without building:

```bat
pip install -r requirements.txt
python main.py
```

## Running tests

```bat
pip install -r requirements.txt
pytest tests/
```

## Linting

```bat
ruff check .
ruff format .
```
