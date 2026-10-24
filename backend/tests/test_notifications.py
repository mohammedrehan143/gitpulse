"""Unit tests for NotificationService and Discord alerts."""

from __future__ import annotations

import httpx
import pytest

from backend.src.gitpulse.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_discord_notification_dispatch(monkeypatch):
    service = NotificationService(discord_webhook_url="https://discord.com/api/webhooks/123/abc")

    async def mock_post(self, url, json=None):
        assert "discord.com" in url
        assert json["embeds"][0]["title"] == "Velocity Alert"
        req = httpx.Request("POST", url)
        return httpx.Response(204, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    success = await service.send_discord_notification(
        title="Velocity Alert",
        description="PR turnaround increased by 15%",
    )
    assert success is True


@pytest.mark.asyncio
async def test_discord_notification_unconfigured():
    service = NotificationService(discord_webhook_url="")
    # Should safely return False without attempting network call
    success = await service.send_discord_notification("Alert", "Test")
    assert success is False
