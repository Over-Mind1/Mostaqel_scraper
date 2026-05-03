from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
from urllib.parse import urlencode, urlsplit, urlunsplit

from fastapi import FastAPI
import uvicorn

from .config import load_settings
from .filters import ProjectFilter, load_filter_config
from .notifier import TelegramNotifier
from .runner import AlertRunner, run_forever
from .scraper import MostaqlScraper
from .state import SeenProjectsStore


# FastAPI app for Render health checks
app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "Bot and Scraper are running!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


def run_api_server():
    """Run the FastAPI server in a background thread."""
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor Mostaqel open projects and send Telegram alerts for new matching projects.",
    )
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Do not send Telegram alerts")
    parser.add_argument(
        "--alert-existing",
        action="store_true",
        help="On first run, alert existing visible projects instead of bootstrapping state",
    )
    parser.add_argument("--filters", default="filters.yml", help="Path to filter YAML file")
    parser.add_argument(
        "--state-path",
        default=".state/seen_projects.json",
        help="Path to state JSON for already seen project ids",
    )
    parser.add_argument("--interval", type=int, default=None, help="Polling interval in seconds")
    parser.add_argument("--url", default=None, help="Projects URL to monitor")
    parser.add_argument("--no-dotenv", action="store_true", help="Skip loading .env file")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    logger = logging.getLogger("mostaql-alert")

    settings = load_settings(dotenv_path=None if args.no_dotenv else ".env")

    projects_url = args.url or settings.projects_url
    interval = args.interval or settings.poll_interval

    filter_config = load_filter_config(args.filters)
    project_filter = ProjectFilter(filter_config)

    base = urlsplit(projects_url)
    base_root = urlunsplit((base.scheme, base.netloc, "", "", "")).rstrip("/")
    projects_urls: list[str]
    if filter_config.site_categories:
        projects_base_url = f"{base_root}/projects"
        projects_urls = [
            f"{projects_base_url}?{urlencode({'category': slug.strip('/'), 'sort': 'latest'})}"
            for slug in filter_config.site_categories
            if slug.strip()
        ]
    else:
        projects_urls = [projects_url]

    store = SeenProjectsStore(args.state_path)
    scraper = MostaqlScraper(timeout=settings.request_timeout)

    notifier = None
    if not args.dry_run:
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            logger.error(
                "Missing Telegram credentials. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID, or use --dry-run"
            )
            return 2
        notifier = TelegramNotifier(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            timeout=settings.request_timeout,
        )
        try:
            notifier.validate_chat()
        except RuntimeError as exc:
            logger.error("Telegram chat validation failed: %s", exc)
            logger.error(
                "Fix TELEGRAM_CHAT_ID and ensure the bot is started or added to the target chat/channel."
            )
            return 2

    runner = AlertRunner(
        scraper=scraper,
        project_filter=project_filter,
        store=store,
        notifier=notifier,
        projects_urls=projects_urls,
        logger=logger,
    )

    if args.once:
        stats = runner.run_once(dry_run=args.dry_run, alert_existing=args.alert_existing)
        logger.info(
            "Done: fetched=%s new=%s matched=%s sent=%s skipped=%s",
            stats["fetched"],
            stats["new"],
            stats["matched"],
            stats["sent"],
            stats["skipped"],
        )
        return 0

    logger.info(
        "Starting monitor loop for %s URL(s) every %s seconds",
        len(projects_urls),
        interval,
    )

    # Start FastAPI server in a background thread to keep Render alive
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    logger.info("FastAPI server started in background")

    # Run the bot in the main thread
    run_forever(
        runner=runner,
        interval_seconds=interval,
        dry_run=args.dry_run,
        alert_existing=args.alert_existing,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
