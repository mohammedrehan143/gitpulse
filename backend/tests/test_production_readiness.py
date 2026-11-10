"""Comprehensive Production Readiness Tests for Data Pipeline, Reconciliation, Collaborator Tracking, and Analytics APIs."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.src.gitpulse.api.main import app
from backend.src.gitpulse.ingestion.pipeline import DataIngestionPipeline
from backend.src.gitpulse.services.activity_service import GitActivityService
from backend.src.gitpulse.services.reconciliation_service import DataReconciliationService
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import (
    CommitRecord,
    ContributorRecord,
    DeveloperMetric,
    Repository,
    SyncCheckpoint,
)


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()


@pytest.mark.asyncio
async def test_pipeline_checkpoints_and_contributors():
    """Verifies that full analytical ingestion creates checkpoints, contributors, reviews, and daily metrics."""
    owner = "acme-corp"
    repo_name = "pipeline-test-repo"

    pipeline = DataIngestionPipeline()
    result = await pipeline.run_pipeline(owner, repo_name, incremental=True, max_pages=1)

    assert result["status"] == "SUCCESS"
    assert result["target_repo"] == f"{owner}/{repo_name}"
    assert result["records_processed"] > 0

    async with AsyncSessionLocal() as session:
        repo = (
            await session.execute(
                select(Repository).where(Repository.full_name == f"{owner}/{repo_name}")
            )
        ).scalar_one_or_none()
        assert repo is not None

        # Verify Checkpoints
        cp_stmt = select(SyncCheckpoint).where(SyncCheckpoint.repo_id == repo.id)
        cps = list((await session.execute(cp_stmt)).scalars().all())
        resource_types = {c.resource_type for c in cps}
        assert "commits" in resource_types
        assert "pull_requests" in resource_types
        assert "issues" in resource_types
        assert "contributors" in resource_types

        # Verify Contributors
        contrib_stmt = select(ContributorRecord).where(ContributorRecord.repo_id == repo.id)
        contribs = list((await session.execute(contrib_stmt)).scalars().all())
        assert len(contribs) > 0

        # Verify DeveloperMetric
        met_stmt = select(DeveloperMetric).where(DeveloperMetric.repo_id == repo.id)
        metrics = list((await session.execute(met_stmt)).scalars().all())
        assert len(metrics) > 0


@pytest.mark.asyncio
async def test_data_reconciliation_service():
    """Verifies that reconciliation service detects state, backfills, and produces an audit report."""
    owner = "acme-corp"
    repo_name = "reconciliation-test-repo"

    recon_service = DataReconciliationService()
    report = await recon_service.reconcile_repository(owner, repo_name)

    assert report["status"] == "RECONCILED"
    assert report["repository"] == f"{owner}/{repo_name}"
    assert "commits" in report
    assert "pull_requests" in report
    assert "issues" in report
    assert report["metrics_recalculated"] is True


@pytest.mark.asyncio
async def test_collaborator_activity_persistence():
    """Verifies that collaborator events are persisted and not discarded when author != owner."""
    owner = "org-enterprise"
    repo_name = "collaborator-suite"
    collaborator = "external-partner-dev"

    activity_service = GitActivityService()

    test_sha = "collab_sha_uniq_150_v2"
    # 1. Collaborator commits
    commit_res = await activity_service.record_commit_activity(
        repo=f"{owner}/{repo_name}",
        actor=collaborator,
        message="feat: implement collaborator integration module",
        sha=test_sha,
        lines_added=150,
        lines_deleted=20,
        notify_discord=False,
    )
    assert commit_res["repo_id"] > 0
    assert commit_res["status"] == "SUCCESS"

    # 2. Collaborator generic event
    evt_res = await activity_service.record_generic_event(
        repo=f"{owner}/{repo_name}",
        event_type="PullRequestReviewEvent",
        actor=collaborator,
        action="submitted",
        summary=f"Collaborator {collaborator} approved PR #42",
        raw_payload={"review": {"state": "APPROVED"}},
    )
    assert evt_res["event_id"] != ""

    # Verify DB state
    async with AsyncSessionLocal() as session:
        repo = (
            await session.execute(
                select(Repository).where(Repository.full_name == f"{owner}/{repo_name}")
            )
        ).scalar_one_or_none()
        assert repo is not None

        c_rec = (
            await session.execute(
                select(CommitRecord).where(
                    CommitRecord.repo_id == repo.id,
                    CommitRecord.sha == test_sha,
                )
            )
        ).scalar_one_or_none()
        assert c_rec is not None
        assert c_rec.author_name == collaborator
        assert c_rec.lines_added == 150


@pytest.mark.asyncio
async def test_api_repository_stats():
    """Verifies GET /api/v1/repos/{owner}/{repo}/stats returns real database aggregations."""
    owner = "acme-corp"
    repo_name = "api-stats-test"

    # Seed data via pipeline
    pipeline = DataIngestionPipeline()
    await pipeline.run_pipeline(owner, repo_name, incremental=False, max_pages=1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/repos/{owner}/{repo_name}/stats")
        assert resp.status_code == 200
        data = resp.json()

        assert data["repository"] == f"{owner}/{repo_name}"
        assert data["total_commits"] >= 0
        assert data["total_contributors"] >= 0
        assert "checkpoints" in data
        assert isinstance(data["checkpoints"], list)


@pytest.mark.asyncio
async def test_api_pulls_and_issues_endpoints():
    """Verifies GET /api/v1/repos/{owner}/{repo}/pulls and /issues."""
    owner = "acme-corp"
    repo_name = "api-prs-issues-test"

    pipeline = DataIngestionPipeline()
    await pipeline.run_pipeline(owner, repo_name, incremental=False, max_pages=1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Pulls
        pr_resp = await client.get(f"/api/v1/repos/{owner}/{repo_name}/pulls?limit=10")
        assert pr_resp.status_code == 200
        pr_data = pr_resp.json()
        assert pr_data["repository"] == f"{owner}/{repo_name}"
        assert "pull_requests" in pr_data

        # Issues
        iss_resp = await client.get(f"/api/v1/repos/{owner}/{repo_name}/issues?limit=10")
        assert iss_resp.status_code == 200
        iss_data = iss_resp.json()
        assert iss_data["repository"] == f"{owner}/{repo_name}"
        assert "issues" in iss_data


@pytest.mark.asyncio
async def test_api_contributors_endpoint():
    """Verifies GET /api/v1/repos/{owner}/{repo}/contributors."""
    owner = "acme-corp"
    repo_name = "api-contrib-test"

    pipeline = DataIngestionPipeline()
    await pipeline.run_pipeline(owner, repo_name, incremental=False, max_pages=1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/repos/{owner}/{repo_name}/contributors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["repository"] == f"{owner}/{repo_name}"
        assert data["total_count"] >= 0
        assert "contributors" in data


@pytest.mark.asyncio
async def test_api_sync_and_reconcile_endpoints():
    """Verifies POST /api/v1/repos/{owner}/{repo}/sync and /reconcile endpoints."""
    owner = "acme-corp"
    repo_name = "api-sync-recon-test"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Sync
        sync_resp = await client.post(
            f"/api/v1/repos/{owner}/{repo_name}/sync?incremental=true&max_pages=1"
        )
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["status"] == "SUCCESS"
        assert sync_data["target_repo"] == f"{owner}/{repo_name}"

        # Reconcile
        recon_resp = await client.post(f"/api/v1/repos/{owner}/{repo_name}/reconcile")
        assert recon_resp.status_code == 200
        recon_data = recon_resp.json()
        assert recon_data["status"] == "RECONCILED"
        assert recon_data["metrics_recalculated"] is True
