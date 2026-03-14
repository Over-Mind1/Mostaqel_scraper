from __future__ import annotations

from datetime import datetime, timezone
from html import escape

import requests

from .models import Project


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, timeout: int = 20) -> None:
        if not bot_token:
            raise ValueError("Missing TELEGRAM_BOT_TOKEN")
        if not chat_id:
            raise ValueError("Missing TELEGRAM_CHAT_ID")

        self.chat_id = chat_id
        self.timeout = timeout
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        self.api_url = f"{self.api_base}/sendMessage"

    def validate_chat(self) -> None:
        response = requests.post(
            f"{self.api_base}/getChat",
            timeout=self.timeout,
            json={"chat_id": self.chat_id},
        )

        if response.status_code >= 400:
            body = response.text[:300]
            if "chat not found" in body.lower():
                raise RuntimeError(
                    f"Chat not found for TELEGRAM_CHAT_ID={self.chat_id}. "
                    "Open a chat with your bot first (or add bot to group/channel), then use the correct chat id."
                )
            raise RuntimeError(f"Telegram chat validation failed [{response.status_code}]: {body}")

        payload = response.json()
        if not payload.get("ok", False):
            description = str(payload.get("description", "Unknown error"))
            if "chat not found" in description.lower():
                raise RuntimeError(
                    f"Chat not found for TELEGRAM_CHAT_ID={self.chat_id}. "
                    "Open a chat with your bot first (or add bot to group/channel), then use the correct chat id."
                )
            raise RuntimeError(f"Telegram chat validation failed: {payload}")

    def send_project(self, project: Project) -> None:
        message = self._build_message(project)

        response = requests.post(
            self.api_url,
            timeout=self.timeout,
            json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
        )

        if response.status_code >= 400:
            body = response.text[:300]
            if "chat not found" in body.lower():
                raise RuntimeError(
                    f"Telegram chat not found for TELEGRAM_CHAT_ID={self.chat_id}. "
                    "Check chat id and make sure the bot can access that chat."
                )
            raise RuntimeError(
                f"Telegram send failed [{response.status_code}]: {body}"
            )

        payload = response.json()
        if not payload.get("ok", False):
            raise RuntimeError(f"Telegram send failed: {payload}")

    def _build_message(self, project: Project) -> str:
        title = escape(project.title)
        url = escape(project.url)
        summary = escape(project.summary[:500])
        client = escape(project.client_name or "غير محدد")
        bids = escape(project.bids_text or (str(project.bids_count) if project.bids_count is not None else "غير محدد"))
        posted = escape(project.published_raw or "غير محدد")

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        return (
            "🚨 <b>مشروع جديد على مستقل</b>\n"
            f"<b>العنوان:</b> <a href=\"{url}\">{title}</a>\n"
            f"<b>العميل:</b> {client}\n"
            f"<b>وقت النشر:</b> {posted}\n"
            f"<b>العروض:</b> {bids}\n"
            f"<b>الوصف:</b> {summary}\n"
            f"<b>ID:</b> <code>{project.project_id}</code>\n"
            f"<b>Checked at:</b> {now}"
        )
