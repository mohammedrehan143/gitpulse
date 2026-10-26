"""Comprehensive tests for GitHub Profile Monitor and Universal Discord Dispatcher."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.gitpulse.api.main import app
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.services.notification_service import NotificationService
from backend.src.gitpulse.services.profile_monitor import ProfileMonitorService


@pytest.mark.asyncio
async def test_notify_github_event_types(monkeypatch):
    """Verifies that notify_github_event correctly parses and formats all event types."""
    dispatched = []

    async def mock_send(self, title, description, color=0x38BDF8, fields=None):
        dispatched.append(
            {"title": title, "description": description, "color": color, "fields": fields}
        )
        return True

    monkeypatch.setattr(NotificationService, "send_discord_notification", mock_send)
    notifier = NotificationService(discord_webhook_url="https://discord.com/api/webhooks/mock/test")

    # 1. Test PushEvent
    push_ev = {
        "id": "1001",
        "type": "PushEvent",
        "repo": {"name": "mohammedrehan143/organic-repo"},
        "actor": {"login": "mohammedrehan143"},
        "payload": {
            "ref": "refs/heads/main",
            "commits": [{"id": "abc1234", "message": "feat: new organic model"}],
        },
    }
    res = await notifier.notify_github_event(push_ev)
    assert res is True
    assert "Push" in dispatched[-1]["title"]
    assert "mohammedrehan143/organic-repo" in dispatched[-1]["title"]

    # 2. Test PullRequestEvent
    pr_ev = {
        "id": "1002",
        "type": "PullRequestEvent",
        "repo": {"name": "mohammedrehan143/organic-repo"},
        "actor": {"login": "mohammedrehan143"},
        "payload": {
            "action": "opened",
            "number": 12,
            "pull_request": {
                "title": "Add async pipeline",
                "number": 12,
                "html_url": "https://github.com/pr/12",
            },
        },
    }
    res = await notifier.notify_github_event(pr_ev)
    assert res is True
    assert "Pull Request OPENED" in dispatched[-1]["title"]
    assert "#12" in dispatched[-1]["title"]

    # 3. Test IssuesEvent
    issue_ev = {
        "id": "1003",
        "type": "IssuesEvent",
        "repo": {"name": "mohammedrehan143/organic-repo"},
        "actor": {"login": "mohammedrehan143"},
        "payload": {
            "action": "closed",
            "number": 5,
            "issue": {
                "title": "Fix memory leak",
                "number": 5,
                "html_url": "https://github.com/issues/5",
            },
        },
    }
    res = await notifier.notify_github_event(issue_ev)
    assert res is True
    assert "Issue CLOSED" in dispatched[-1]["title"]

    # 4. Test CreateEvent (branch)
    create_ev = {
        "id": "1004",
        "type": "CreateEvent",
        "repo": {"name": "mohammedrehan143/organic-repo"},
        "actor": {"login": "mohammedrehan143"},
        "payload": {"ref_type": "branch", "ref": "feature/analytics"},
    }
    res = await notifier.notify_github_event(create_ev)
    assert res is True
    assert "New Branch Created" in dispatched[-1]["title"]

    # 5. Test DeleteEvent
    del_ev = {
        "id": "1005",
        "type": "DeleteEvent",
        "repo": {"name": "mohammedrehan143/organic-repo"},
        "actor": {"login": "mohammedrehan143"},
        "payload": {"ref_type": "branch", "ref": "old-feature"},
    }
    res = await notifier.notify_github_event(del_ev)
    assert res is True
    assert "Branch Deleted" in dispatched[-1]["title"]


@pytest.mark.asyncio
async def test_profile_monitor_deduplication_and_dispatch(monkeypatch):
    """Verifies that ProfileMonitorService only alerts on newly discovered events."""
    mock_events = [
        {
            "id": "ev_01",
            "type": "PushEvent",
            "repo": {"name": "mohammedrehan143/repo-a"},
            "actor": {"login": "mohammedrehan143"},
            "payload": {"ref": "refs/heads/main", "commits": [{"id": "c1", "message": "Initial"}]},
        },
        {
            "id": "ev_02",
            "type": "PushEvent",
            "repo": {"name": "mohammedrehan143/repo-b"},
            "actor": {"login": "mohammedrehan143"},
            "payload": {"ref": "refs/heads/dev", "commits": [{"id": "c2", "message": "Second"}]},
        },
    ]

    async def mock_fetch_user_events(self, username, page=1, per_page=30):
        return list(mock_events)

    dispatched = []

    async def mock_notify_github_event(self, event):
        dispatched.append(event["id"])
        return True

    monkeypatch.setattr(GitHubClient, "fetch_user_events", mock_fetch_user_events)
    monkeypatch.setattr(NotificationService, "notify_github_event", mock_notify_github_event)

    monitor = ProfileMonitorService(username="mohammedrehan143", interval_seconds=10)
    # Pre-prime ev_01 so only ev_02 is new
    monitor.seen_event_ids.add("ev_01")
    monitor._is_primed = True

    count = await monitor.poll_and_notify()
    assert count == 1
    assert "ev_02" in dispatched
    assert "ev_01" not in dispatched

    # Second poll without changes should dispatch 0
    count2 = await monitor.poll_and_notify()
    assert count2 == 0


@pytest.mark.asyncio
async def test_profile_poll_api_endpoints(monkeypatch):
    """Verifies that POST /api/v1/profile/poll and /api/v1/profile/{username}/poll succeed."""

    async def mock_poll(self):
        return 2

    monkeypatch.setattr(ProfileMonitorService, "poll_and_notify", mock_poll)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Default user
        res1 = await client.post("/api/v1/profile/poll")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "SUCCESS"
        assert data1["username"] == "mohammedrehan143"
        assert data1["new_alerts_dispatched"] == 2

        # Specific user
        res2 = await client.post("/api/v1/profile/mohammedrehan143/poll")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "SUCCESS"
        assert data2["username"] == "mohammedrehan143"
