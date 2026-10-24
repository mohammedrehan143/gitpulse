"""Tests for GitPulse Lightweight Ingestion Scheduler."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.ingestion.runner import run_ingestion_pipeline
from backend.src.gitpulse.scheduler import GitPulseScheduler


@pytest.mark.asyncio
async def test_scheduler_initialization_defaults():
    scheduler = GitPulseScheduler()
    assert scheduler.interval_minutes == (
        getattr(settings, "INGESTION_SCHEDULE_INTERVAL_MINUTES", None)
        or getattr(settings, "REPO_DISCOVERY_INTERVAL_MINUTES", 60)
    )
    assert scheduler.is_running is False
    assert scheduler.is_job_active is False
    assert scheduler.run_count == 0
    assert scheduler.last_run_status is None
    assert scheduler.next_run_time is None


@pytest.mark.asyncio
async def test_scheduler_custom_interval_and_zero_fallback():
    # Custom valid interval
    custom_scheduler = GitPulseScheduler(interval_minutes=15, max_pages=3, notify_discord=True)
    assert custom_scheduler.interval_minutes == 15
    assert custom_scheduler.max_pages == 3
    assert custom_scheduler.notify_discord is True

    # Zero or negative interval should fallback to 60 minutes
    fallback_scheduler = GitPulseScheduler(interval_minutes=0)
    assert fallback_scheduler.interval_minutes == 60


@pytest.mark.asyncio
async def test_scheduler_execute_job_success():
    scheduler = GitPulseScheduler(interval_minutes=30)
    mock_summary = {"owner/repo-a": 12, "owner/repo-b": 7}

    with patch(
        "backend.src.gitpulse.scheduler.run_ingestion_pipeline",
        new=AsyncMock(return_value=mock_summary),
    ) as mock_run:
        result = await scheduler.execute_job()

        assert mock_run.called
        assert result["status"] == "SUCCESS"
        assert result["run_id"] == 1
        assert result["summary"] == mock_summary
        assert scheduler.run_count == 1
        assert scheduler.last_run_status == "SUCCESS"
        assert scheduler.is_job_active is False


@pytest.mark.asyncio
async def test_scheduler_execute_job_failure_resilience():
    scheduler = GitPulseScheduler(interval_minutes=30)
    simulated_error = RuntimeError("GitHub API rate limit exhausted (403)")

    with patch(
        "backend.src.gitpulse.scheduler.run_ingestion_pipeline",
        new=AsyncMock(side_effect=simulated_error),
    ):
        # execute_job should handle the exception gracefully without raising unhandled error
        result = await scheduler.execute_job()

        assert result["status"] == "FAILED"
        assert result["run_id"] == 1
        assert "GitHub API rate limit exhausted" in result["error"]
        assert scheduler.run_count == 1
        assert scheduler.last_run_status == "FAILED"
        assert scheduler.is_job_active is False


@pytest.mark.asyncio
async def test_scheduler_prevents_overlapping_runs():
    scheduler = GitPulseScheduler(interval_minutes=60)

    # Acquire the lock to simulate an ingestion cycle actively executing
    await scheduler._lock.acquire()
    assert scheduler.is_job_active is True

    try:
        # A concurrent execution trigger should be safely skipped
        result = await scheduler.execute_job()
        assert result["status"] == "SKIPPED"
        assert "still executing" in result["reason"]
        assert scheduler.run_count == 0
    finally:
        scheduler._lock.release()

    assert scheduler.is_job_active is False


@pytest.mark.asyncio
async def test_scheduler_graceful_shutdown():
    scheduler = GitPulseScheduler(interval_minutes=60)
    scheduler._is_running = True

    await scheduler.stop()
    assert scheduler._shutdown_event.is_set()
    assert scheduler.is_running is False


@pytest.mark.asyncio
async def test_scheduler_run_forever_immediate_startup_and_stop():
    scheduler = GitPulseScheduler(interval_minutes=60)
    mock_summary = {"sample/repo": 4}

    with patch(
        "backend.src.gitpulse.scheduler.run_ingestion_pipeline",
        new=AsyncMock(return_value=mock_summary),
    ):
        # Start run_forever in a background asyncio task
        task = asyncio.create_task(scheduler.run_forever())

        # Yield control briefly so the immediate run executes
        await asyncio.sleep(0.05)

        assert scheduler.is_running is True
        assert scheduler.run_count >= 1
        assert scheduler.last_run_status == "SUCCESS"
        assert scheduler.next_run_time is not None

        # Signal stop
        await scheduler.stop()
        await task

        assert scheduler.is_running is False


@pytest.mark.asyncio
async def test_run_ingestion_pipeline_with_auto_discovery():
    discovered_repos = ["org/service-alpha", "org/service-beta"]
    mock_summary = {"org/service-alpha": 10, "org/service-beta": 8}

    with (
        patch(
            "backend.src.gitpulse.services.repository_service.RepositoryService.sync_repositories",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "backend.src.gitpulse.services.repository_service.RepositoryService.get_target_repo_names",
            new=AsyncMock(return_value=discovered_repos),
        ),
        patch(
            "backend.src.gitpulse.ingestion.runner.ingest_repository_events",
            new=AsyncMock(return_value=mock_summary),
        ) as mock_ingest,
    ):
        summary = await run_ingestion_pipeline(target_repos=None, max_pages=1)
        assert summary == mock_summary
        mock_ingest.assert_called_once_with(
            repos=discovered_repos,
            max_pages=1,
            publish_to_kafka=False,
            persist_to_db=True,
            notify_discord=False,
        )
