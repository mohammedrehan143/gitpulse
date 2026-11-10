"""AI Context Builder for GitPulse Groq Engineering Intelligence.

Retrieves and normalizes verified database records from Supabase / SQLite to build
grounded, hallucination-free context payloads for the Groq LLM layer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from backend.src.gitpulse.storage.database import AsyncSessionLocal
from backend.src.gitpulse.storage.models import (
    CommitRecord,
    ContributorRecord,
    IssueRecord,
    PullRequestRecord,
    Repository,
    ReviewRecord,
)


def _normalize_dt(dt: datetime | None) -> datetime | None:
    """Ensures datetime is UTC offset-aware to avoid naive/aware subtraction errors."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class AIContextBuilder:
    """Builds grounded structured contexts directly from the relational database."""

    @staticmethod
    async def get_repository_context(
        owner: str,
        repo_name: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Constructs full repository engineering context including commits, PRs, issues, and contributors."""
        full_name = f"{owner}/{repo_name}"
        cutoff = datetime.now(UTC) - timedelta(days=days)

        async with AsyncSessionLocal() as session:
            # 1. Repository Metadata
            r_stmt = select(Repository).where(Repository.full_name == full_name)
            repo = (await session.execute(r_stmt)).scalar_one_or_none()
            if not repo:
                return {
                    "error": f"Repository {full_name} not found in database",
                    "full_name": full_name,
                    "verified_facts": {},
                }

            repo_id = repo.id

            # Check if this repository has any commits; if 0, attempt on-demand ingestion
            count_stmt = select(func.count(CommitRecord.id)).where(CommitRecord.repo_id == repo_id)
            c_count = (await session.execute(count_stmt)).scalar() or 0

            if c_count == 0:
                try:
                    from backend.src.gitpulse.ingestion.pipeline import DataIngestionPipeline

                    pipeline = DataIngestionPipeline()
                    await pipeline.run_pipeline(owner, repo_name, incremental=False, max_pages=3)
                except Exception:
                    pass

            # 2. Commits & Lines (All-Time and Timeframe Window)
            all_c_stmt = (
                select(CommitRecord)
                .where(CommitRecord.repo_id == repo_id)
                .order_by(CommitRecord.committed_at.desc())
            )
            all_commits = list((await session.execute(all_c_stmt)).scalars().all())

            window_commits = [
                c
                for c in all_commits
                if _normalize_dt(c.committed_at) and _normalize_dt(c.committed_at) >= cutoff
            ]

            total_added = sum(c.lines_added for c in all_commits)
            total_deleted = sum(c.lines_deleted for c in all_commits)
            window_added = sum(c.lines_added for c in window_commits)
            window_deleted = sum(c.lines_deleted for c in window_commits)
            commit_authors = {c.author_name for c in all_commits if c.author_name}

            display_commits = window_commits if window_commits else all_commits[:15]
            recent_commit_samples = [
                {
                    "sha": c.sha[:8],
                    "author": c.author_name,
                    "message": c.message.split("\n")[0][:100],
                    "date": c.committed_at.strftime("%Y-%m-%d %H:%M") if c.committed_at else "",
                    "added": c.lines_added,
                    "deleted": c.lines_deleted,
                }
                for c in display_commits
            ]

            latest_c = all_commits[0] if all_commits else None
            latest_commit_date = (
                latest_c.committed_at.strftime("%Y-%m-%d %H:%M UTC")
                if (latest_c and latest_c.committed_at)
                else "None"
            )
            latest_commit_message = latest_c.message.split("\n")[0][:120] if latest_c else "None"
            latest_commit_author = latest_c.author_name if latest_c else "None"

            # Inactive days detection
            committed_days = {
                c.committed_at.strftime("%Y-%m-%d") for c in window_commits if c.committed_at
            }
            all_days = {
                (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)
            }
            inactive_days_count = len(all_days - committed_days)

            # 3. Pull Requests
            pr_stmt = (
                select(PullRequestRecord)
                .where(PullRequestRecord.repo_id == repo_id)
                .order_by(PullRequestRecord.created_at.desc())
            )
            all_prs = list((await session.execute(pr_stmt)).scalars().all())

            open_prs = [p for p in all_prs if p.state == "open"]
            merged_prs = [p for p in all_prs if p.merged_at is not None]
            closed_prs = [p for p in all_prs if p.state == "closed" and p.merged_at is None]

            # Long running PRs (> 7 days open)
            now_dt = datetime.now(UTC)
            long_running_prs = []
            for p in open_prs:
                p_created = _normalize_dt(p.created_at)
                if p_created and (now_dt - p_created).total_seconds() > 7 * 86400:
                    long_running_prs.append(
                        {
                            "number": p.number,
                            "title": p.title,
                            "author": p.author_login,
                            "days_open": round((now_dt - p_created).total_seconds() / 86400.0, 1),
                            "additions": p.additions,
                            "deletions": p.deletions,
                        }
                    )

            # Cycle times
            cycle_diffs = []
            for p in merged_prs:
                p_created = _normalize_dt(p.created_at)
                p_merged = _normalize_dt(p.merged_at)
                if p_created and p_merged and (p_merged - p_created).total_seconds() > 0:
                    cycle_diffs.append((p_merged - p_created).total_seconds() / 3600.0)
            avg_cycle_hours = round(sum(cycle_diffs) / len(cycle_diffs), 1) if cycle_diffs else 0.0

            # 4. Issues
            iss_stmt = select(IssueRecord).where(IssueRecord.repo_id == repo_id)
            all_issues = list((await session.execute(iss_stmt)).scalars().all())
            open_issues = [i for i in all_issues if i.state == "open"]
            closed_issues = [i for i in all_issues if i.state == "closed"]

            # 5. Contributors
            contrib_stmt = (
                select(ContributorRecord)
                .where(ContributorRecord.repo_id == repo_id)
                .order_by(ContributorRecord.contributions_count.desc())
                .limit(10)
            )
            contribs = list((await session.execute(contrib_stmt)).scalars().all())
            contributor_roster = [
                {
                    "login": c.login,
                    "contributions": c.contributions_count,
                    "commits": c.commits_count,
                    "prs": c.prs_count,
                    "issues": c.issues_count,
                }
                for c in contribs
            ]

            churn = (
                round(total_deleted / (total_added + total_deleted), 2)
                if (total_added + total_deleted) > 0
                else 0.0
            )

            return {
                "repository": full_name,
                "description": repo.description or "No description provided",
                "default_branch": repo.default_branch,
                "stars": repo.stars_count,
                "forks": repo.forks_count,
                "is_active": repo.is_active,
                "timeframe_days": days,
                "data_freshness": (
                    repo.last_synced_at.isoformat()
                    if repo.last_synced_at
                    else datetime.now(UTC).isoformat()
                ),
                "verified_facts": {
                    "all_time_commits_count": len(all_commits),
                    "window_commits_count": len(window_commits),
                    "total_commits": len(all_commits),
                    "active_authors_count": len(commit_authors),
                    "all_time_lines_added": total_added,
                    "all_time_lines_deleted": total_deleted,
                    "lines_added": total_added,
                    "lines_deleted": total_deleted,
                    "window_lines_added": window_added,
                    "window_lines_deleted": window_deleted,
                    "code_churn_rate": churn,
                    "inactive_days": inactive_days_count,
                    "total_pull_requests_count": len(all_prs),
                    "open_prs_count": len(open_prs),
                    "merged_prs_count": len(merged_prs),
                    "closed_prs_count": len(closed_prs),
                    "avg_pr_cycle_time_hours": avg_cycle_hours,
                    "long_running_prs_count": len(long_running_prs),
                    "total_issues_count": len(all_issues),
                    "open_issues_count": len(open_issues),
                    "closed_issues_count": len(closed_issues),
                    "latest_commit_date": latest_commit_date,
                    "latest_commit_message": latest_commit_message,
                    "latest_commit_author": latest_commit_author,
                    "primary_contributor": latest_commit_author,
                    "tracked_contributors_count": len(contributor_roster),
                },
                "samples": {
                    "recent_commits": recent_commit_samples,
                    "long_running_prs": long_running_prs[:5],
                    "top_contributors": contributor_roster[:5],
                },
            }

    @staticmethod
    async def get_pr_context(owner: str, repo_name: str, pr_number: int) -> dict[str, Any]:
        """Constructs detailed context for an individual pull request including review timeline."""
        full_name = f"{owner}/{repo_name}"

        async with AsyncSessionLocal() as session:
            stmt = (
                select(PullRequestRecord)
                .join(Repository, PullRequestRecord.repo_id == Repository.id)
                .where(Repository.full_name == full_name, PullRequestRecord.number == pr_number)
            )
            pr = (await session.execute(stmt)).scalar_one_or_none()
            if not pr:
                return {"error": f"PR #{pr_number} not found in {full_name}"}

            # Fetch associated reviews
            rev_stmt = (
                select(ReviewRecord)
                .where(ReviewRecord.pr_id == pr.id)
                .order_by(ReviewRecord.submitted_at.asc())
            )
            reviews = list((await session.execute(rev_stmt)).scalars().all())

            cycle_hours = None
            pr_created = _normalize_dt(pr.created_at)
            pr_merged = _normalize_dt(pr.merged_at)
            pr_reviewed = _normalize_dt(pr.first_reviewed_at)

            if pr_merged and pr_created:
                cycle_hours = round((pr_merged - pr_created).total_seconds() / 3600.0, 1)

            review_delay_hours = None
            if pr_reviewed and pr_created:
                review_delay_hours = round((pr_reviewed - pr_created).total_seconds() / 3600.0, 1)

            return {
                "repository": full_name,
                "number": pr.number,
                "title": pr.title,
                "body": pr.body or "No description provided",
                "state": pr.state,
                "author": pr.author_login,
                "created_at": pr.created_at.isoformat(),
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,
                "first_reviewed_at": (
                    pr.first_reviewed_at.isoformat() if pr.first_reviewed_at else None
                ),
                "cycle_time_hours": cycle_hours,
                "first_review_delay_hours": review_delay_hours,
                "verified_metrics": {
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "total_changes": pr.additions + pr.deletions,
                    "changed_files": pr.changed_files,
                    "review_comments_count": pr.review_comments_count,
                    "reviews_count": len(reviews),
                },
                "reviews": [
                    {
                        "reviewer": r.reviewer_login,
                        "state": r.state,
                        "submitted_at": r.submitted_at.isoformat(),
                        "summary": (r.body or "")[:150],
                    }
                    for r in reviews
                ],
            }

    @staticmethod
    async def get_developer_context(
        owner: str, repo_name: str, developer_login: str
    ) -> dict[str, Any]:
        """Constructs evidence-based contribution summary for an individual developer."""
        full_name = f"{owner}/{repo_name}"

        async with AsyncSessionLocal() as session:
            repo = (
                await session.execute(select(Repository).where(Repository.full_name == full_name))
            ).scalar_one_or_none()
            if not repo:
                return {"error": f"Repository {full_name} not found"}

            # Contributor record
            c_stmt = select(ContributorRecord).where(
                ContributorRecord.repo_id == repo.id,
                ContributorRecord.login == developer_login,
            )
            contrib = (await session.execute(c_stmt)).scalar_one_or_none()

            # Commits
            commits_stmt = (
                select(CommitRecord)
                .where(
                    CommitRecord.repo_id == repo.id,
                    CommitRecord.author_name == developer_login,
                )
                .order_by(CommitRecord.committed_at.desc())
                .limit(25)
            )
            commits = list((await session.execute(commits_stmt)).scalars().all())

            # PRs authored
            prs_stmt = (
                select(PullRequestRecord)
                .where(
                    PullRequestRecord.repo_id == repo.id,
                    PullRequestRecord.author_login == developer_login,
                )
                .order_by(PullRequestRecord.created_at.desc())
            )
            prs = list((await session.execute(prs_stmt)).scalars().all())

            total_added = sum(c.lines_added for c in commits)
            total_deleted = sum(c.lines_deleted for c in commits)

            return {
                "repository": full_name,
                "developer": developer_login,
                "verified_metrics": {
                    "total_contributions": (
                        contrib.contributions_count if contrib else len(commits) + len(prs)
                    ),
                    "commits_count": len(commits),
                    "prs_authored_count": len(prs),
                    "prs_merged_count": len([p for p in prs if p.merged_at is not None]),
                    "lines_added": total_added,
                    "lines_deleted": total_deleted,
                    "first_active": (
                        contrib.first_contributed_at.isoformat()
                        if contrib and contrib.first_contributed_at
                        else (commits[-1].committed_at.isoformat() if commits else None)
                    ),
                    "last_active": (
                        contrib.last_contributed_at.isoformat()
                        if contrib and contrib.last_contributed_at
                        else (commits[0].committed_at.isoformat() if commits else None)
                    ),
                },
                "recent_commits": [
                    {
                        "sha": c.sha[:8],
                        "message": c.message.split("\n")[0][:100],
                        "date": c.committed_at.strftime("%Y-%m-%d") if c.committed_at else "",
                        "added": c.lines_added,
                        "deleted": c.lines_deleted,
                    }
                    for c in commits[:10]
                ],
                "recent_prs": [
                    {
                        "number": p.number,
                        "title": p.title,
                        "state": p.state,
                        "merged": p.merged_at is not None,
                    }
                    for p in prs[:5]
                ],
            }

    @staticmethod
    async def get_global_engineering_context(days: int = 7) -> dict[str, Any]:
        """Retrieves system-wide repository intelligence for cross-repository questions."""
        cutoff = datetime.now(UTC) - timedelta(days=days)

        async with AsyncSessionLocal() as session:
            repos = list(
                (await session.execute(select(Repository).order_by(Repository.pushed_at.desc())))
                .scalars()
                .all()
            )

            repo_summaries = []
            for r in repos[:15]:
                # Commit count in timeframe
                c_cnt = (
                    await session.execute(
                        select(func.count(CommitRecord.id)).where(
                            CommitRecord.repo_id == r.id,
                            CommitRecord.committed_at >= cutoff,
                        )
                    )
                ).scalar() or 0

                # Open PRs
                open_pr_cnt = (
                    await session.execute(
                        select(func.count(PullRequestRecord.id)).where(
                            PullRequestRecord.repo_id == r.id,
                            PullRequestRecord.state == "open",
                        )
                    )
                ).scalar() or 0

                # Latest commit
                latest_c = (
                    await session.execute(
                        select(CommitRecord)
                        .where(CommitRecord.repo_id == r.id)
                        .order_by(CommitRecord.committed_at.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()

                repo_summaries.append(
                    {
                        "name": r.full_name,
                        "is_active": r.is_active,
                        "commits_in_window": c_cnt,
                        "open_prs": open_pr_cnt,
                        "last_activity": (
                            r.pushed_at.strftime("%Y-%m-%d %H:%M") if r.pushed_at else "None"
                        ),
                        "latest_commit_author": latest_c.author_name if latest_c else "None",
                    }
                )

            # Longest open PRs across platform
            longest_prs = (
                await session.execute(
                    select(PullRequestRecord, Repository.full_name)
                    .join(Repository, PullRequestRecord.repo_id == Repository.id)
                    .where(PullRequestRecord.state == "open")
                    .order_by(PullRequestRecord.created_at.asc())
                    .limit(5)
                )
            ).all()

            longest_open_prs = [
                {
                    "repo": pr_row[1],
                    "number": pr_row[0].number,
                    "title": pr_row[0].title,
                    "author": pr_row[0].author_login,
                    "created_at": pr_row[0].created_at.strftime("%Y-%m-%d"),
                }
                for pr_row in longest_prs
            ]

            return {
                "timeframe_days": days,
                "total_monitored_repositories": len(repos),
                "repositories": repo_summaries,
                "longest_open_pull_requests": longest_open_prs,
                "generated_at": datetime.now(UTC).isoformat(),
            }
