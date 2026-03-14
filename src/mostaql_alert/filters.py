from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from .models import Project


@dataclass(slots=True)
class FilterConfig:
    site_categories: list[str]
    include_keywords: list[str]
    exclude_keywords: list[str]
    include_categories: list[str]
    exclude_categories: list[str]
    max_age_hours: Optional[float]
    max_bids: Optional[int]
    min_bids: Optional[int]
    min_budget: Optional[float]
    max_budget: Optional[float]
    strict_missing_fields: bool


@dataclass(slots=True)
class FilterResult:
    matched: bool
    reason: str = ""


def _as_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def load_filter_config(path: str) -> FilterConfig:
    raw = {}
    file_path = Path(path)

    if file_path.exists():
        loaded = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = loaded

    return FilterConfig(
        site_categories=_as_list(raw.get("site_categories")),
        include_keywords=_as_list(raw.get("include_keywords")),
        exclude_keywords=_as_list(raw.get("exclude_keywords")),
        include_categories=_as_list(raw.get("include_categories")),
        exclude_categories=_as_list(raw.get("exclude_categories")),
        max_age_hours=raw.get("max_age_hours"),
        max_bids=raw.get("max_bids"),
        min_bids=raw.get("min_bids"),
        min_budget=raw.get("min_budget"),
        max_budget=raw.get("max_budget"),
        strict_missing_fields=bool(raw.get("strict_missing_fields", False)),
    )


class ProjectFilter:
    def __init__(self, config: FilterConfig) -> None:
        self.config = config

    def evaluate(self, project: Project, now_utc: Optional[datetime] = None) -> FilterResult:
        now_utc = now_utc or datetime.now(timezone.utc)

        searchable_text = f"{project.title} {project.summary}".lower()

        if self.config.include_keywords:
            if not any(word.lower() in searchable_text for word in self.config.include_keywords):
                return FilterResult(False, "missing include_keywords")

        if self.config.exclude_keywords:
            if any(word.lower() in searchable_text for word in self.config.exclude_keywords):
                return FilterResult(False, "matched exclude_keywords")

        if self.config.include_categories:
            if project.category is None:
                if self.config.strict_missing_fields:
                    return FilterResult(False, "missing category")
            elif project.category not in self.config.include_categories:
                return FilterResult(False, "category not included")

        if self.config.exclude_categories and project.category in self.config.exclude_categories:
            return FilterResult(False, "category excluded")

        if self.config.max_age_hours is not None:
            if project.published_at is None:
                if self.config.strict_missing_fields:
                    return FilterResult(False, "missing publish time")
            else:
                age_hours = (now_utc - project.published_at).total_seconds() / 3600
                if age_hours > float(self.config.max_age_hours):
                    return FilterResult(False, "too old")

        if self.config.max_bids is not None:
            if project.bids_count is None:
                if self.config.strict_missing_fields:
                    return FilterResult(False, "missing bids")
            elif project.bids_count > int(self.config.max_bids):
                return FilterResult(False, "bids above maximum")

        if self.config.min_bids is not None:
            if project.bids_count is None:
                if self.config.strict_missing_fields:
                    return FilterResult(False, "missing bids")
            elif project.bids_count < int(self.config.min_bids):
                return FilterResult(False, "bids below minimum")

        if self.config.min_budget is not None:
            if project.budget_min is None and project.budget_max is None:
                if self.config.strict_missing_fields:
                    return FilterResult(False, "missing budget")
            else:
                comparable_budget = project.budget_max if project.budget_max is not None else project.budget_min
                if comparable_budget is not None and comparable_budget < float(self.config.min_budget):
                    return FilterResult(False, "budget below minimum")

        if self.config.max_budget is not None:
            if project.budget_min is None and project.budget_max is None:
                if self.config.strict_missing_fields:
                    return FilterResult(False, "missing budget")
            else:
                comparable_budget = project.budget_min if project.budget_min is not None else project.budget_max
                if comparable_budget is not None and comparable_budget > float(self.config.max_budget):
                    return FilterResult(False, "budget above maximum")

        return FilterResult(True, "matched")
