from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import Project

PROJECT_ID_PATTERN = re.compile(r"/project/(\d+)")
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _to_ascii_digits(value: str) -> str:
    return value.translate(ARABIC_DIGITS)


def _normalize_spaces(value: str) -> str:
    return " ".join(value.split())


def _extract_int(text: str) -> Optional[int]:
    normalized = _to_ascii_digits(text)
    numbers = re.findall(r"\d+", normalized)
    if not numbers:
        return None
    return int(numbers[0])


def _extract_project_id(url: str) -> Optional[int]:
    match = PROJECT_ID_PATTERN.search(url)
    if not match:
        return None
    return int(match.group(1))


def _parse_datetime(raw: str) -> Optional[datetime]:
    if not raw:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


class MostaqlScraper:
    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = requests.Session()

        retry = Retry(
            total=3,
            backoff_factor=0.7,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch_projects(self, url: str, category: Optional[str] = None) -> list[Project]:
        response = self.session.get(
            url,
            timeout=self.timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) MostaqlAlertBot/1.0",
                "Accept-Language": "ar,en-US;q=0.8,en;q=0.7",
            },
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("tr.project-row")
        projects: list[Project] = []

        for row in rows:
            project = self._parse_row(row, category=category)
            if project is not None:
                projects.append(project)

        return projects

    def _parse_row(self, row, category: Optional[str] = None) -> Optional[Project]:
        title_link = row.select_one("h2 a[href*='/project/']")
        if not title_link:
            return None

        url = (title_link.get("href") or "").strip()
        if not url:
            return None

        project_id = _extract_project_id(url)
        if project_id is None:
            return None

        title = _normalize_spaces(title_link.get_text(" ", strip=True))

        brief_link = row.select_one("p.project__brief a")
        summary = ""
        if brief_link:
            summary = _normalize_spaces(brief_link.get_text(" ", strip=True))

        client_name = ""
        published_raw = ""
        published_at: Optional[datetime] = None
        bids_text = ""
        bids_count: Optional[int] = None

        meta_items = row.select("ul.project__meta li.text-muted")
        for item in meta_items:
            text = _normalize_spaces(item.get_text(" ", strip=True))
            if not text:
                continue

            if item.select_one("i.fa-user"):
                client_name = text
                continue

            time_el = item.select_one("time")
            if time_el is not None:
                published_raw = _normalize_spaces(time_el.get_text(" ", strip=True))
                datetime_attr = (time_el.get("datetime") or "").strip()
                published_at = _parse_datetime(datetime_attr)
                continue

            if "عرض" in text or "عروض" in text:
                bids_text = text
                bids_count = _extract_int(text)
                continue

            if "أضف أول عرض" in text:
                bids_text = text
                bids_count = 0

        return Project(
            project_id=project_id,
            url=url,
            title=title,
            summary=summary,
            client_name=client_name,
            published_at=published_at,
            published_raw=published_raw,
            bids_count=bids_count,
            bids_text=bids_text,
            category=category,
        )


def to_logger_summary(project: Project) -> str:
    return f"{project.project_id} | {project.title} | bids={project.bids_count}"


def log_projects(logger: logging.Logger, projects: list[Project]) -> None:
    for project in projects:
        logger.debug(to_logger_summary(project))
