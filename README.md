# Mostaqel New Projects Telegram Alert

Python monitor that scrapes Mostaqel open projects, detects only **new** projects, filters them, and sends alerts to Telegram.

## Features

- Polls `https://mostaql.com/projects` (or custom URL)
- Detects new projects using persistent state (`.state/seen_projects.json`)
- Flexible filter file (`filters.yml`)
- Telegram bot alerts for matched projects
- First-run bootstrap to avoid old-project spam
- `--dry-run` mode for testing without Telegram

## Project Structure

- `monitor.py`: root entrypoint
- `src/mostaql_alert/scraper.py`: fetch + parse project rows
- `src/mostaql_alert/filters.py`: filter engine
- `src/mostaql_alert/notifier.py`: Telegram sending
- `src/mostaql_alert/state.py`: seen IDs persistence
- `src/mostaql_alert/runner.py`: run cycle + loop
- `src/mostaql_alert/main.py`: CLI options
- `filters.yml`: editable filtering rules

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your Telegram data:

```env
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_CHAT_ID
```

## Usage

### 1) Test parser/filter only (no Telegram send)

```bash
python monitor.py --once --dry-run --verbose
```

### 2) Normal one-time run (sends alerts for new matched projects)

```bash
python monitor.py --once
```

### 3) Continuous monitor loop

```bash
python monitor.py
```

### 4) Force first run to alert current visible projects

```bash
python monitor.py --once --alert-existing
```

## Filters (`filters.yml`)

`site_categories` contains native Mostaqel category slugs. By default, all native categories are included. To stop monitoring a category, delete its slug from `site_categories`.

You can adjust:

- `site_categories`: which native category pages to monitor
- `include_keywords`: only notify when title/brief contains any
- `exclude_keywords`: skip projects containing these words
- `max_age_hours`: ignore old projects
- `max_bids` / `min_bids`
- `min_budget` / `max_budget` (used when budget data exists)
- `strict_missing_fields`: if `true`, missing fields cause reject

## Notes

- The parser targets current Mostaqel table rows (`tr.project-row`).
- If Mostaqel changes HTML structure, selectors may need updates.
- On first run, current projects are saved as seen (no alerts) unless `--alert-existing` is used.
