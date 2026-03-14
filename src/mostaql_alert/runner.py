from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .filters import ProjectFilter
from .models import Project
from .notifier import TelegramNotifier
from .scraper import MostaqlScraper
from .state import SeenProjectsStore


class AlertRunner:
    def __init__(
        self,
        scraper: MostaqlScraper,
        project_filter: ProjectFilter,
        store: SeenProjectsStore,
        notifier: Optional[TelegramNotifier],
        projects_urls: list[str],
        logger: logging.Logger,
    ) -> None:
        self.scraper = scraper
        self.project_filter = project_filter
        self.store = store
        self.notifier = notifier
        self.projects_urls = projects_urls
        self.logger = logger

    @staticmethod
    def _extract_category_slug(url: str) -> Optional[str]:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        category_param = query.get("category", [])
        if category_param and category_param[0].strip():
            return category_param[0].strip()

        path = parsed.path.strip("/")
        if not path.startswith("projects"):
            return None
        parts = path.split("/")
        if len(parts) >= 2 and parts[1]:
            return parts[1]
        return None

    def run_once(
        self,
        dry_run: bool = False,
        alert_existing: bool = False,
    ) -> dict:
        projects_by_id: dict[int, Project] = {}

        for url in self.projects_urls:
            category = self._extract_category_slug(url)
            fetched = self.scraper.fetch_projects(url, category=category)
            self.logger.info("Fetched %s projects from %s", len(fetched), url)
            for project in fetched:
                projects_by_id[project.project_id] = project

        projects = list(projects_by_id.values())
        self.logger.info("Fetched %s unique projects", len(projects))

        if not projects:
            return {
                "fetched": 0,
                "new": 0,
                "matched": 0,
                "sent": 0,
                "skipped": 0,
            }

        first_run_bootstrap = self.store.is_first_run and not alert_existing
        if first_run_bootstrap:
            self.store.mark_many(p.project_id for p in projects)
            self.logger.info(
                "First run bootstrap: saved %s projects without sending alerts", len(projects)
            )
            return {
                "fetched": len(projects),
                "new": 0,
                "matched": 0,
                "sent": 0,
                "skipped": len(projects),
            }

        new_projects = [project for project in projects if not self.store.has(project.project_id)]
        self.logger.info("Detected %s new projects", len(new_projects))

        now_utc = datetime.now(timezone.utc)
        matched: list[Project] = []
        filtered_out_ids: list[int] = []

        for project in new_projects:
            result = self.project_filter.evaluate(project, now_utc=now_utc)
            if result.matched:
                matched.append(project)
            else:
                filtered_out_ids.append(project.project_id)
                self.logger.debug("Filtered out %s (%s)", project.project_id, result.reason)

        sent_ids: list[int] = []
        if dry_run:
            for project in matched:
                self.logger.info("[DRY RUN] Match: %s - %s", project.project_id, project.title)
                sent_ids.append(project.project_id)
        else:
            for project in matched:
                if self.notifier is None:
                    self.logger.warning(
                        "No notifier configured, cannot send project %s", project.project_id
                    )
                    continue
                self.notifier.send_project(project)
                sent_ids.append(project.project_id)
                self.logger.info("Alert sent for project %s", project.project_id)

        self.store.mark_many([*filtered_out_ids, *sent_ids])

        return {
            "fetched": len(projects),
            "new": len(new_projects),
            "matched": len(matched),
            "sent": len(sent_ids),
            "skipped": len(filtered_out_ids),
        }



def run_forever(runner: AlertRunner, interval_seconds: int, dry_run: bool, alert_existing: bool) -> None:
    while True:
        try:
            stats = runner.run_once(dry_run=dry_run, alert_existing=alert_existing)
            runner.logger.info(
                "Cycle done: fetched=%s new=%s matched=%s sent=%s skipped=%s",
                stats["fetched"],
                stats["new"],
                stats["matched"],
                stats["sent"],
                stats["skipped"],
            )
        except Exception as exc:
            runner.logger.exception("Cycle failed: %s", exc)

        time.sleep(max(interval_seconds, 15))
