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


@pytest.mark.asyncio
async def test_notify_git_actions(monkeypatch):
    service = NotificationService(discord_webhook_url="https://discord.com/api/webhooks/mock")
    sent = []

    async def mock_post(self, url, json=None):
        sent.append(json)
        req = httpx.Request("POST", url)
        return httpx.Response(204, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    # 1. Test push notification
    res_push = await service.notify_git_push(
        repo_name="org/repo",
        pusher="developer",
        branch="main",
        commits=[{"id": "abc1234", "message": "feat: init"}],
    )
    assert res_push is True
    assert "New Git Pushed" in sent[-1]["embeds"][0]["title"]
    assert "New git pushed!" in sent[-1]["embeds"][0]["description"]

    # 2. Test pull notification
    res_pull = await service.notify_git_pull(
        repo_name="org/repo",
        actor="developer",
        action="merged",
        pr_number=42,
        pr_title="feat: pipeline",
    )
    assert res_pull is True
    assert "New Git Pulled" in sent[-1]["embeds"][0]["title"]
    assert "New git pulled!" in sent[-1]["embeds"][0]["description"]

    # 3. Test commit notification
    res_commit = await service.notify_git_commit(
        repo_name="org/repo",
        author="developer",
        sha="deadbeef",
        message="refactor: clean up",
    )
    assert res_commit is True
    assert "New Git Committed" in sent[-1]["embeds"][0]["title"]
    assert "New git committed!" in sent[-1]["embeds"][0]["description"]
