from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


class SeenProjectsStore:
    def __init__(self, path: str, max_items: int = 5000) -> None:
        self.path = Path(path)
        self.max_items = max_items
        self._seen: list[int] = []
        self._seen_set: set[int] = set()
        self._loaded = False

    @property
    def is_first_run(self) -> bool:
        self._ensure_loaded()
        return not self.path.exists() or not self._seen

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        if self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                seen = payload.get("seen_project_ids", [])
                self._seen = [int(item) for item in seen]
                self._seen_set = set(self._seen)
            except (ValueError, TypeError, json.JSONDecodeError):
                self._seen = []
                self._seen_set = set()

        self._loaded = True

    def has(self, project_id: int) -> bool:
        self._ensure_loaded()
        return project_id in self._seen_set

    def mark_many(self, project_ids: Iterable[int]) -> None:
        self._ensure_loaded()
        updated = False

        for project_id in project_ids:
            value = int(project_id)
            if value in self._seen_set:
                continue
            self._seen.append(value)
            self._seen_set.add(value)
            updated = True

        if not updated:
            return

        if len(self._seen) > self.max_items:
            self._seen = self._seen[-self.max_items :]
            self._seen_set = set(self._seen)

        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"seen_project_ids": self._seen}
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
