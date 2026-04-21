# Mostaqel New Projects Telegram Alert

A lightweight Python monitor that watches Mostaqel open projects, keeps track of what has already been seen, filters by your rules, and sends Telegram alerts for matching new posts.

## Tech Stack

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Requests](https://img.shields.io/badge/Requests-20232A?style=for-the-badge&logo=requests&logoColor=white)](https://requests.readthedocs.io/)
[![Beautiful Soup](https://img.shields.io/badge/Beautiful%20Soup-4EAA25?style=for-the-badge&logo=beautifulsoup&logoColor=white)](https://www.crummy.com/software/BeautifulSoup/)
[![PyYAML](https://img.shields.io/badge/PyYAML-000000?style=for-the-badge&logo=yaml&logoColor=white)](https://pyyaml.org/)
[![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org/)

## What It Does

- Monitors `https://mostaql.com/projects` or a custom Mostaqel projects URL
- Detects only newly published projects using persistent state in `.state/seen_projects.json`
- Applies YAML-based filtering from `filters.yml`
- Sends formatted Telegram alerts for matching projects
- Supports first-run bootstrapping to avoid old-project spam
- Includes `--dry-run` for safe local testing

## Project Structure

```text
.
├── docker-compose.yml
├── Dockerfile
├── filters.yml
├── monitor.py
├── README.md
├── requirements.txt
├── setup-linux.sh
├── src
│   ├── mostaql_alert
│   │   ├── config.py
│   │   ├── filters.py
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── notifier.py
│   │   ├── runner.py
│   │   ├── scraper.py
│   │   └── state.py
│   └── utils
│       └── __init__.py
└── structure.txt
```

Key files:

- `monitor.py`: root entrypoint
- `src/mostaql_alert/main.py`: CLI parsing and application flow
- `src/mostaql_alert/scraper.py`: fetches and parses project rows
- `src/mostaql_alert/filters.py`: evaluates filter rules
- `src/mostaql_alert/notifier.py`: sends Telegram messages
- `src/mostaql_alert/state.py`: persists seen project IDs
- `src/mostaql_alert/runner.py`: runs one cycle or the polling loop
- `src/mostaql_alert/config.py`: loads environment settings
- `filters.yml`: editable filter configuration

## Requirements

- Python 3.10+
- A Telegram bot token and chat ID for notifications
- Internet access to fetch Mostaqel project listings

## Quick Start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` with your Telegram credentials:

```env
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_CHAT_ID
```

Optional environment values:

```env
MOSTAQL_URL=https://mostaql.com/projects
POLL_INTERVAL=120
REQUEST_TIMEOUT=20
```

## Docker

Build and run with Docker:

```bash
docker build -t mostaql-alert .
docker run --rm --env-file .env -v "$PWD/.state:/app/.state" -v "$PWD/filters.yml:/app/filters.yml:ro" mostaql-alert
```

Use Docker Compose for a long-running monitor:

```bash
docker compose up --build
```

## Fast Linux Setup

Run the bootstrap script to create the virtual environment, install dependencies, and prepare `.env`:

```bash
bash setup-linux.sh
```

After that, activate the environment and start the monitor:

```bash
source venv/bin/activate
python monitor.py
```

## Usage

Run one cycle in dry-run mode to test parsing and filtering without sending Telegram messages:

```bash
python monitor.py --once --dry-run --verbose
```

Run once and send alerts for new matching projects:

```bash
python monitor.py --once
```

Start continuous monitoring:

```bash
python monitor.py
```

Alert the currently visible projects on the first run instead of bootstrapping state:

```bash
python monitor.py --once --alert-existing
```

## CLI Options

- `--once`: run a single monitoring cycle and exit
- `--dry-run`: skip Telegram sending
- `--alert-existing`: alert current projects on the first run
- `--filters`: path to the filter YAML file, default `filters.yml`
- `--state-path`: path to the seen-projects JSON file, default `.state/seen_projects.json`
- `--interval`: polling interval in seconds
- `--url`: custom projects URL
- `--no-dotenv`: skip loading `.env`
- `--verbose`: enable debug logging

## Filtering

`filters.yml` controls what gets alerted. By default, all native categories are monitored. Remove any category slug from `site_categories` to stop watching it.

Useful filter fields include:

- `site_categories`: category slugs to monitor
- `include_keywords`: require at least one matching keyword
- `exclude_keywords`: block projects containing specific words
- `max_age_hours`: ignore older projects
- `min_bids` and `max_bids`: limit by bid count
- `min_budget` and `max_budget`: limit by budget when available
- `strict_missing_fields`: reject projects when important fields are missing

## How It Works

1. The scraper fetches the Mostaqel projects page.
2. The filter engine evaluates each project against `filters.yml`.
3. Seen project IDs are stored in `.state/seen_projects.json`.
4. New matching projects are sent to Telegram.

## Notes

- The parser currently targets Mostaqel table rows with `tr.project-row`.
- If Mostaqel changes its HTML structure, selectors may need to be updated.
- On the first normal run, existing projects are recorded as seen so you do not receive a backlog of alerts.
