"""Tests for Data Engineering Foundation, Quality Checks, and Ingestion Pipeline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from backend.src.gitpulse.data_science.quality import DataQualityChecker
from backend.src.gitpulse.ingestion.pipeline import DataIngestionPipeline
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import (
    PipelineRun,
    PullRequestRecord,
    Repository,
)


@pytest.mark.asyncio
async def test_data_quality_checker_timestamps():
    now = datetime.now(UTC)
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)
    tomorrow = now + timedelta(days=1)

    # Valid sequence
    valid, err = DataQualityChecker.validate_timestamp_sequence(two_days_ago, yesterday)
    assert valid is True
    assert err is None

    # Closed before created
    valid, err = DataQualityChecker.validate_timestamp_sequence(yesterday, two_days_ago)
    assert valid is False
    assert "precedes creation" in err

    # Far future creation
    valid, err = DataQualityChecker.validate_timestamp_sequence(tomorrow, None)
    assert valid is False
    assert "in the future" in err


@pytest.mark.asyncio
async def test_data_quality_checker_pr_metrics():
    valid, err = DataQualityChecker.validate_pr_metrics(100, 20, 5)
    assert valid is True

    valid, err = DataQualityChecker.validate_pr_metrics(-1, 20, 5)
    assert valid is False
    assert "Negative additions" in err


@pytest.mark.asyncio
async def test_data_quality_audit_daily_series():
    # Healthy 14-day sequence
    daily_records = {f"2026-10-{d:02d}": d * 2 for d in range(1, 15)}
    audit = DataQualityChecker.audit_daily_series(daily_records, min_expected_days=7)
    assert audit["valid"] is True
    assert audit["total_calendar_days"] == 14
    assert audit["quality_score"] > 0.8

    # Empty dataset
    empty_audit = DataQualityChecker.audit_daily_series({})
    assert empty_audit["valid"] is False
    assert empty_audit["status"] == "EMPTY_DATASET"


@pytest.mark.asyncio
async def test_data_ingestion_pipeline_idempotency():
    await init_db()
    pipeline = DataIngestionPipeline()

    # Run 1
    result1 = await pipeline.run_pipeline("test-org", "pipeline-repo", max_pages=1)
    assert result1["status"] == "SUCCESS"
    assert result1["records_processed"] > 0

    # Verify PipelineRun record created
    async with AsyncSessionLocal() as session:
        stmt = select(PipelineRun).where(PipelineRun.target_repo == "test-org/pipeline-repo")
        res = await session.execute(stmt)
        runs = res.scalars().all()
        assert len(runs) >= 1
        latest_run = runs[-1]
        assert latest_run.status == "SUCCESS"
        assert latest_run.records_processed > 0

    # Run 2 (Idempotent run should not duplicate records)
    result2 = await pipeline.run_pipeline("test-org", "pipeline-repo", max_pages=1)
    assert result2["status"] == "SUCCESS"

    async with AsyncSessionLocal() as session:
        # Check total PR count for repository
        repo_stmt = select(Repository).where(Repository.full_name == "test-org/pipeline-repo")
        repo_res = await session.execute(repo_stmt)
        repo = repo_res.scalar_one()

        pr_stmt = select(PullRequestRecord).where(PullRequestRecord.repo_id == repo.id)
        pr_res = await session.execute(pr_stmt)
        prs = pr_res.scalars().all()
        # Verify no duplicate github_ids
        pr_gh_ids = [p.github_id for p in prs]
        assert len(pr_gh_ids) == len(set(pr_gh_ids)), "Duplicate PR records detected!"
