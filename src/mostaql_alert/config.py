from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(slots=True)
class AppSettings:
    telegram_bot_token: str
    telegram_chat_id: str
    projects_url: str
    poll_interval: int
    request_timeout: int


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_settings(dotenv_path: str | None = ".env") -> AppSettings:
    if dotenv_path:
        _load_dotenv(Path(dotenv_path))

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    projects_url = os.getenv("MOSTAQL_URL", "https://mostaql.com/projects").strip()
    poll_interval = int(os.getenv("POLL_INTERVAL", "120"))
    request_timeout = int(os.getenv("REQUEST_TIMEOUT", "20"))

    return AppSettings(
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        projects_url=projects_url,
        poll_interval=poll_interval,
        request_timeout=request_timeout,
    )
