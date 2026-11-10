"""Tests for GitPulse Unified Git Activity & Real-Time Persistence Service."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.src.gitpulse.services.activity_service import (
    activity_service,
    parse_repo_coordinates,
    resolve_effective_user,
)
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import CommitRecord, GitHubEvent, Repository


@pytest.mark.asyncio
async def test_resolve_effective_user_dynamic():
    """Verifies user resolution is dynamic with zero hardcoding."""
    user = resolve_effective_user("custom_contributor")
    assert user == "custom_contributor"

    # With empty/None user, falls back dynamically to environment or git config or developer
    fallback_user = resolve_effective_user(None)
    assert fallback_user and len(fallback_user) > 0


def test_parse_repo_coordinates():
    """Verifies coordinate parsing handles various formats dynamically."""
    o1, n1, f1 = parse_repo_coordinates("owner/repo")
    assert o1 == "owner"
    assert n1 == "repo"
    assert f1 == "owner/repo"

    o2, n2, f2 = parse_repo_coordinates("https://github.com/my-org/my-service.git")
    assert o2 == "my-org"
    assert n2 == "my-service"
    assert f2 == "my-org/my-service"

    o3, n3, f3 = parse_repo_coordinates("standalone-repo", default_actor="local-dev")
    assert n3 == "standalone-repo"
    assert f3.endswith("standalone-repo")


@pytest.mark.asyncio
async def test_record_commit_activity_creates_new_repo_and_persists():
    """Verifies committing to a brand new repo registers the repo, commit, and event in DB."""
    await init_db()
    test_repo = "dynamic-suite-org/brand-new-auto-discovered-repo"
    test_actor = "test-author-007"
    test_sha = "deadbeef1234567890abcdef"
    test_msg = "feat: initial dynamic commit"

    res = await activity_service.record_commit_activity(
        repo=test_repo,
        actor=test_actor,
        branch="main",
        sha=test_sha,
        message=test_msg,
        commits=[{"id": test_sha, "message": test_msg, "author": {"name": test_actor}}],
        notify_discord=False,
    )

    assert res["status"] == "SUCCESS"
    assert res["repository"] == test_repo

    async with AsyncSessionLocal() as session:
        # 1. Verify repository was created in DB
        res_r = await session.execute(select(Repository).where(Repository.full_name == test_repo))
        repo_obj = res_r.scalar_one_or_none()
        assert repo_obj is not None
        assert repo_obj.monitoring_status == "MONITORED"
        assert repo_obj.is_active is True

        # 2. Verify commit was saved in DB
        res_c = await session.execute(
            select(CommitRecord).where(
                CommitRecord.repo_id == repo_obj.id, CommitRecord.sha == test_sha
            )
        )
        commit_obj = res_c.scalar_one_or_none()
        assert commit_obj is not None
        assert commit_obj.message == test_msg
        assert commit_obj.author_name == test_actor

        # 3. Verify event was saved in DB
        res_e = await session.execute(
            select(GitHubEvent).where(
                GitHubEvent.repo_id == repo_obj.id, GitHubEvent.event_type == "PushEvent"
            )
        )
        event_obj = res_e.scalars().first()
        assert event_obj is not None
        assert event_obj.actor_login == test_actor


@pytest.mark.asyncio
async def test_record_generic_event_creates_repo_and_event():
    """Verifies generic events (e.g. CreateEvent) automatically register new repo and event in DB."""
    await init_db()
    new_repo = "startup-inc/novel-ai-agent"
    test_actor = "creator-alice"

    res = await activity_service.record_generic_event(
        repo=new_repo,
        event_type="CreateEvent",
        actor=test_actor,
        action="created",
        summary="Created new repository",
        raw_payload={"ref_type": "repository"},
        repo_metadata={"description": "Cutting edge autonomous agent"},
    )

    assert res["status"] == "SUCCESS"
    assert res["repository"] == new_repo

    async with AsyncSessionLocal() as session:
        res_r = await session.execute(select(Repository).where(Repository.full_name == new_repo))
        repo_obj = res_r.scalar_one_or_none()
        assert repo_obj is not None
        assert repo_obj.description == "Cutting edge autonomous agent"
        assert repo_obj.monitoring_status == "MONITORED"

        res_e = await session.execute(
            select(GitHubEvent).where(
                GitHubEvent.repo_id == repo_obj.id, GitHubEvent.event_type == "CreateEvent"
            )
        )
        event_obj = res_e.scalars().first()
        assert event_obj is not None
        assert event_obj.actor_login == test_actor
