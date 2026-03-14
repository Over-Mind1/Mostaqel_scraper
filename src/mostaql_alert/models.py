from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class Project:
    project_id: int
    url: str
    title: str
    summary: str
    client_name: str
    published_at: Optional[datetime]
    published_raw: str
    bids_count: Optional[int]
    bids_text: str
    category: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    currency: Optional[str] = None
