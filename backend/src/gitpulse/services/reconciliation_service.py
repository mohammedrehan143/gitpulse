"""Data Reconciliation Service for Auditing and Healing Drift between GitHub and GitPulse Storage."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.ingestion.pipeline import DataIngestionPipeline
from backend.src.gitpulse.storage.database import AsyncSessionLocal
from backend.src.gitpulse.storage.models import (
    CommitRecord,
    ContributorRecord,
    IssueRecord,
    PullRequestRecord,
)


class DataReconciliationService:
    """Detects missing entities between remote GitHub state and local database, and heals drift."""

    def __init__(self, client: GitHubClient | None = None):
        self.client = client or GitHubClient()
        self.pipeline = DataIngestionPipeline(self.client)

    async def reconcile_repository(self, owner: str, repo_name: str) -> dict[str, Any]:
        """Audits commits, PRs, issues, and contributors, inserting missing records and refreshing metrics."""
        full_name = f"{owner}/{repo_name}"
        logger.info("Starting data reconciliation audit for %s", full_name)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                repo = await self.pipeline._get_or_create_repo(session, owner, repo_name)
                repo_id = repo.id

                # Initial counts
                c_before = (
                    await session.execute(
                        select(func.count(CommitRecord.id)).where(CommitRecord.repo_id == repo_id)
                    )
                ).scalar() or 0
                pr_before = (
                    await session.execute(
                        select(func.count(PullRequestRecord.id)).where(
                            PullRequestRecord.repo_id == repo_id
                        )
                    )
                ).scalar() or 0
                iss_before = (
                    await session.execute(
                        select(func.count(IssueRecord.id)).where(IssueRecord.repo_id == repo_id)
                    )
                ).scalar() or 0

        # Run pipeline ingestion to heal drift and backfill missing items
        pr_res = await self.pipeline.ingest_pull_requests(
            owner, repo_name, incremental=False, max_pages=3
        )
        iss_res = await self.pipeline.ingest_issues(
            owner, repo_name, incremental=False, max_pages=3
        )
        comm_res = await self.pipeline.ingest_commits(
            owner, repo_name, incremental=False, max_pages=3
        )
        contrib_res = await self.pipeline.ingest_contributors(owner, repo_name, max_pages=2)
        rev_res = await self.pipeline.ingest_reviews(owner, repo_name, max_prs=30)

        # Recalculate metrics directly from the reconciled state
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await self.pipeline._compute_and_save_daily_metrics(session, repo_id, days=30)

                c_after = (
                    await session.execute(
                        select(func.count(CommitRecord.id)).where(CommitRecord.repo_id == repo_id)
                    )
                ).scalar() or 0
                pr_after = (
                    await session.execute(
                        select(func.count(PullRequestRecord.id)).where(
                            PullRequestRecord.repo_id == repo_id
                        )
                    )
                ).scalar() or 0
                iss_after = (
                    await session.execute(
                        select(func.count(IssueRecord.id)).where(IssueRecord.repo_id == repo_id)
                    )
                ).scalar() or 0
                contrib_after = (
                    await session.execute(
                        select(func.count(ContributorRecord.id)).where(
                            ContributorRecord.repo_id == repo_id
                        )
                    )
                ).scalar() or 0

        report = {
            "repository": full_name,
            "status": "RECONCILED",
            "reconciled_at": datetime.now(UTC).isoformat(),
            "commits": {
                "before": c_before,
                "after": c_after,
                "newly_added": max(0, c_after - c_before),
                "ingest_processed": comm_res.get("processed", 0),
            },
            "pull_requests": {
                "before": pr_before,
                "after": pr_after,
                "newly_added": max(0, pr_after - pr_before),
                "ingest_processed": pr_res.get("processed", 0),
            },
            "issues": {
                "before": iss_before,
                "after": iss_after,
                "newly_added": max(0, iss_after - iss_before),
                "ingest_processed": iss_res.get("processed", 0),
            },
            "contributors": {
                "total_tracked": contrib_after,
                "ingest_processed": contrib_res.get("processed", 0),
            },
            "reviews": {
                "ingest_processed": rev_res.get("processed", 0),
            },
            "metrics_recalculated": True,
        }
        logger.info("Completed data reconciliation for %s: %s", full_name, report)
        return report
