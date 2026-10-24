"""Notification and Webhook Dispatch Service (Discord, etc.)."""

from __future__ import annotations

from typing import Any

import httpx

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger


class NotificationService:
    """Dispatches event alerts and metrics digests to external channels."""

    def __init__(self, discord_webhook_url: str | None = None):
        self.webhook_url = (
            discord_webhook_url if discord_webhook_url is not None else settings.DISCORD_WEBHOOK_URL
        )

    async def send_discord_notification(
        self,
        title: str,
        description: str,
        color: int = 0x38BDF8,  # GitPulse Cyan
        fields: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Sends rich embed notification to configured Discord webhook."""
        if not self.webhook_url:
            logger.debug("Discord webhook URL not configured. Skipping alert.")
            return False

        payload = {
            "username": "GitPulse Alerts",
            "avatar_url": "https://avatars.githubusercontent.com/u/9919?s=200&v=4",
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": color,
                    "fields": fields or [],
                    "footer": {"text": "GitPulse Analytics Platform"},
                }
            ],
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(self.webhook_url, json=payload)
                if resp.status_code in (200, 204):
                    logger.info("Discord notification sent successfully: %s", title)
                    return True
                else:
                    logger.warning(
                        "Discord webhook returned status %d: %s",
                        resp.status_code,
                        resp.text,
                    )
                    return False
            except Exception as exc:
                logger.error("Failed to deliver Discord notification: %s", exc)
                return False
