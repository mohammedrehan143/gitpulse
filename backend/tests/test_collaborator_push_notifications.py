"""Comprehensive Tests for GitPulse Collaborator Push Notifications & Webhook Ingestion.

Validates end-to-end collaborator push notifications, repository identification by immutable GitHub ID,
signature verification, webhook idempotency, multi-subscriber delivery, and multi-branch tracking.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from backend.src.gitpulse.api.main import app
from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.services.notification_service import NotificationService
from backend.src.gitpulse.services.subscription_service import subscription_service
from backend.src.gitpulse.services.webhook_service import webhook_service
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import (
    CommitRecord,
    GitHubEvent,
    Repository,
    WebhookDelivery,
)


def _generate_signature(secret: str, payload_bytes: bytes) -> str:
    """Helper to generate standard GitHub HMAC SHA-256 signature header."""
    return "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
async def clean_webhook_memory():
    """Cleans in-memory and database delivery records before each test."""
    webhook_service._memory_seen_deliveries.clear()
    await init_db()
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(delete(WebhookDelivery))
    except Exception:
        pass


@pytest.mark.asyncio
async def test_repository_owner_pushes_notification_received(monkeypatch):
    """Test 1: Repository owner pushes -> notification received."""
    dispatched_notifications = []

    async def mock_send(self, title, description, color=0x38BDF8, fields=None, webhook_url=None):
        dispatched_notifications.append({
            "title": title,
            "description": description,
            "color": color,
            "fields": fields,
            "webhook_url": webhook_url or self.webhook_url,
        })
        return True

    monkeypatch.setattr(NotificationService, "send_discord_notification", mock_send)

    payload = {
        "repository": {
            "id": 9876501,
            "name": "pulse-repo",
            "full_name": "rehan-owner/pulse-repo",
            "owner": {"login": "rehan-owner", "id": 1001},
        },
        "pusher": {"name": "rehan-owner", "email": "rehan@example.com"},
        "sender": {"login": "rehan-owner", "id": 1001, "avatar_url": "https://avatars.github.com/u/1001"},
        "ref": "refs/heads/main",
        "commits": [
            {
                "id": "c01owner1234567890",
                "message": "feat: owner core update",
                "author": {"name": "rehan-owner", "email": "rehan@example.com", "username": "rehan-owner"},
            }
        ],
    }

    deliv_id = f"deliv-owner-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": deliv_id},
        )
        assert resp.status_code == 202
        assert resp.json()["status"] == "ACCEPTED"

    assert len(dispatched_notifications) >= 1
    item = dispatched_notifications[-1]
    assert "New Git Pushed: rehan-owner/pulse-repo" in item["title"]
    assert "rehan-owner" in item["description"]


@pytest.mark.asyncio
async def test_collaborator_a_pushes_notification_received(monkeypatch):
    """Test 2: Collaborator A pushes -> notification received by repository subscribers."""
    dispatched_notifications = []

    async def mock_send(self, title, description, color=0x38BDF8, fields=None, webhook_url=None):
        dispatched_notifications.append({
            "title": title,
            "description": description,
            "color": color,
            "fields": fields,
            "webhook_url": webhook_url or self.webhook_url,
        })
        return True

    monkeypatch.setattr(NotificationService, "send_discord_notification", mock_send)

    payload = {
        "repository": {
            "id": 9876502,
            "name": "collab-project",
            "full_name": "rehan-owner/collab-project",
            "owner": {"login": "rehan-owner", "id": 1001},
        },
        "pusher": {"name": "alex-dev-local", "email": "alex@collab.io"},
        "sender": {"login": "collaborator_alex", "id": 2002, "avatar_url": "https://avatars.github.com/u/2002"},
        "ref": "refs/heads/main",
        "commits": [
            {
                "id": "c02alex1234567890",
                "message": "fix: resolve memory leak in pipeline",
                "author": {"name": "Alex", "email": "alex@collab.io", "username": "collaborator_alex"},
            }
        ],
    }

    deliv_id = f"deliv-collab-a-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": deliv_id},
        )
        assert resp.status_code == 202
        assert resp.json()["status"] == "ACCEPTED"

    assert len(dispatched_notifications) >= 1
    item = dispatched_notifications[-1]
    # Collaborator is recognized and distinguished from repo owner
    assert "collaborator_alex" in item["description"]
    assert "Collaborator" in item["description"]


@pytest.mark.asyncio
async def test_collaborator_b_pushes_notification_received(monkeypatch):
    """Test 3: Collaborator B pushes -> notification received by repository subscribers."""
    dispatched_notifications = []

    async def mock_send(self, title, description, color=0x38BDF8, fields=None, webhook_url=None):
        dispatched_notifications.append({
            "title": title,
            "description": description,
            "color": color,
            "fields": fields,
            "webhook_url": webhook_url or self.webhook_url,
        })
        return True

    monkeypatch.setattr(NotificationService, "send_discord_notification", mock_send)

    payload = {
        "repository": {
            "id": 9876503,
            "name": "collab-project-b",
            "full_name": "rehan-owner/collab-project-b",
            "owner": {"login": "rehan-owner", "id": 1001},
        },
        "pusher": {"name": "bianca-git", "email": "bianca@collab.io"},
        "sender": {"login": "collaborator_bianca", "id": 3003, "avatar_url": "https://avatars.github.com/u/3003"},
        "ref": "refs/heads/main",
        "commits": [
            {
                "id": "c03bianca1234567890",
                "message": "feat: add forecasting anomaly integration",
                "author": {"name": "Bianca", "email": "bianca@collab.io", "username": "collaborator_bianca"},
            }
        ],
    }

    deliv_id = f"deliv-collab-b-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": deliv_id},
        )
        assert resp.status_code == 202
        assert resp.json()["status"] == "ACCEPTED"

    assert len(dispatched_notifications) >= 1
    item = dispatched_notifications[-1]
    assert "collaborator_bianca" in item["description"]


@pytest.mark.asyncio
async def test_collaborator_pushes_to_different_branch_recorded(monkeypatch):
    """Test 4: Collaborator pushes to a different branch -> activity recorded correctly."""
    dispatched = []

    async def mock_send(self, title, description, color=0x38BDF8, fields=None, webhook_url=None):
        dispatched.append({"title": title, "description": description})
        return True

    monkeypatch.setattr(NotificationService, "send_discord_notification", mock_send)

    target_branch = "feature/collaborator-stream-pipeline"
    payload = {
        "repository": {
            "id": 9876504,
            "name": "multi-branch-repo",
            "full_name": "org-team/multi-branch-repo",
            "owner": {"login": "org-team", "id": 5005},
        },
        "pusher": {"name": "charlie-git", "email": "charlie@collab.io"},
        "sender": {"login": "collaborator_charlie", "id": 4004},
        "ref": f"refs/heads/{target_branch}",
        "commits": [
            {
                "id": "c04charlie123456789",
                "message": "feat: kafka stream handler on branch",
                "author": {"name": "Charlie", "email": "charlie@collab.io", "username": "collaborator_charlie"},
            }
        ],
    }

    deliv_id = f"deliv-branch-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": deliv_id},
        )
        assert resp.status_code == 202

    # Verify database persistence of collaborator event and branch
    await init_db()
    async with AsyncSessionLocal() as session:
        stmt = (
            select(GitHubEvent)
            .join(Repository, GitHubEvent.repo_id == Repository.id)
            .where(Repository.github_id == 9876504)
        )
        res = await session.execute(stmt)
        events = res.scalars().all()
        assert len(events) >= 1
        ev = events[-1]
        assert ev.actor_login == "collaborator_charlie"
        assert target_branch in (ev.payload_summary or "")
        assert ev.raw_payload.get("ref") == f"refs/heads/{target_branch}"

        # Verify CommitRecord persistence
        c_stmt = (
            select(CommitRecord)
            .join(Repository, CommitRecord.repo_id == Repository.id)
            .where(Repository.github_id == 9876504)
        )
        c_res = await session.execute(c_stmt)
        commits_db = c_res.scalars().all()
        assert any(c.sha == "c04charlie123456789" for c in commits_db)


@pytest.mark.asyncio
async def test_duplicate_webhook_delivery_idempotency(monkeypatch):
    """Test 5: Duplicate webhook delivery -> no duplicate notifications."""
    dispatched_count = 0

    async def mock_send(self, title, description, color=0x38BDF8, fields=None, webhook_url=None):
        nonlocal dispatched_count
        dispatched_count += 1
        return True

    monkeypatch.setattr(NotificationService, "send_discord_notification", mock_send)

    delivery_guid = f"github-delivery-uuid-{uuid.uuid4()}"
    payload = {
        "repository": {
            "id": 9876505,
            "name": "idempotent-repo",
            "full_name": "org/idempotent-repo",
            "owner": {"login": "org"},
        },
        "pusher": {"name": "dev"},
        "sender": {"login": "dev_collaborator"},
        "ref": "refs/heads/main",
        "commits": [{"id": "c05idempotent", "message": "idempotent push"}],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First delivery attempt
        resp1 = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": delivery_guid},
        )
        assert resp1.status_code == 202
        assert resp1.json()["status"] == "ACCEPTED"
        assert dispatched_count == 1

        # Second delivery attempt (GitHub retry simulation)
        resp2 = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": delivery_guid},
        )
        assert resp2.status_code == 202
        assert resp2.json()["status"] == "DUPLICATE_SKIPPED"
        # Crucial assertion: Notification count did NOT increase on duplicate delivery
        assert dispatched_count == 1


@pytest.mark.asyncio
async def test_invalid_webhook_signature_rejected(monkeypatch):
    """Test 6: Invalid webhook signature -> request rejected with 401."""
    test_secret = "correct_webhook_secret_key_123"
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", test_secret)

    payload = {"repository": {"id": 111, "full_name": "test/secure-repo"}, "ref": "refs/heads/main"}
    payload_bytes = json.dumps(payload).encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Provide completely wrong signature -> 401
        bad_sig = "sha256=ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        resp_bad = await client.post(
            "/api/v1/webhooks/github",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": bad_sig,
            },
        )
        assert resp_bad.status_code == 401
        assert "Invalid webhook signature" in resp_bad.json()["detail"]

        # 2. Provide signature generated using GITHUB_TOKEN instead of GITHUB_WEBHOOK_SECRET -> 401
        fake_token_sig = _generate_signature("ghp_notTheWebhookSecretToken", payload_bytes)
        resp_token = await client.post(
            "/api/v1/webhooks/github",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": fake_token_sig,
            },
        )
        assert resp_token.status_code == 401
        assert "Invalid webhook signature" in resp_token.json()["detail"]

        # 3. Provide valid signature generated using GITHUB_WEBHOOK_SECRET -> 202
        valid_sig = _generate_signature(test_secret, payload_bytes)
        resp_good = await client.post(
            "/api/v1/webhooks/github",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": valid_sig,
            },
        )
        assert resp_good.status_code == 202


@pytest.mark.asyncio
async def test_multiple_repository_subscribers_all_notified(monkeypatch):
    """Test 7: Multiple repository subscribers -> all eligible users notified."""
    delivered_urls = []

    async def mock_send(self, title, description, color=0x38BDF8, fields=None, webhook_url=None):
        delivered_urls.append(webhook_url or self.webhook_url)
        return True

    monkeypatch.setattr(NotificationService, "send_discord_notification", mock_send)

    repo_gid = 9876507
    repo_name = "multi-subscriber-org/platform"

    # Register multiple subscribers with distinct webhook channels
    sub1_url = "https://discord.com/api/webhooks/channel_user1"
    sub2_url = "https://discord.com/api/webhooks/channel_user2"
    sub3_url = "https://discord.com/api/webhooks/channel_user3_owner"

    await subscription_service.subscribe_user(
        repo_github_id=repo_gid,
        user_id="collaborator_user1",
        webhook_url=sub1_url,
        event_types=["push"],
    )
    await subscription_service.subscribe_user(
        repo_github_id=repo_gid,
        user_id="collaborator_user2",
        webhook_url=sub2_url,
        event_types=["push"],
    )
    await subscription_service.subscribe_user(
        repo_github_id=repo_gid,
        user_id="repo_owner",
        webhook_url=sub3_url,
        event_types=["all"],
    )

    payload = {
        "repository": {
            "id": repo_gid,
            "name": "platform",
            "full_name": repo_name,
            "owner": {"login": "multi-subscriber-org", "type": "Organization"},
        },
        "pusher": {"name": "contributor-john"},
        "sender": {"login": "contributor_john", "id": 7007},
        "ref": "refs/heads/release/v1.0",
        "commits": [{"id": "c07multi", "message": "feat: release candidate"}],
    }

    deliv_id = f"deliv-multi-sub-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": deliv_id},
        )
        assert resp.status_code == 202

    # Assert that ALL three distinct subscriber webhooks received notifications
    assert sub1_url in delivered_urls
    assert sub2_url in delivered_urls
    assert sub3_url in delivered_urls


@pytest.mark.asyncio
async def test_organization_repository_support(monkeypatch):
    """Test 8: Push to an organization repository correctly tracks and alerts."""
    dispatched = []

    async def mock_send(self, title, description, color=0x38BDF8, fields=None, webhook_url=None):
        dispatched.append({"title": title, "description": description})
        return True

    monkeypatch.setattr(NotificationService, "send_discord_notification", mock_send)

    payload = {
        "repository": {
            "id": 9876508,
            "name": "data-infra",
            "full_name": "enterprise-org/data-infra",
            "owner": {"login": "enterprise-org", "type": "Organization"},
            "organization": "enterprise-org",
        },
        "pusher": {"name": "dana-git"},
        "sender": {"login": "dana_dev", "avatar_url": "https://avatars.github.com/u/8008"},
        "ref": "refs/heads/main",
        "commits": [
            {
                "id": "c08org123",
                "message": "perf: speed up ingestion",
                "author": {"name": "Dana", "username": "dana_dev"},
            }
        ],
    }

    deliv_id = f"deliv-org-{uuid.uuid4()}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": deliv_id},
        )
        assert resp.status_code == 202

    # Verify repository was tracked with immutable github_id and org owner
    await init_db()
    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.github_id == 9876508)
        res = await session.execute(stmt)
        repo = res.scalar_one_or_none()
        assert repo is not None
        assert repo.owner == "enterprise-org"
        assert repo.full_name == "enterprise-org/data-infra"
