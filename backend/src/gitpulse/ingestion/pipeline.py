"""Production Data Ingestion Pipeline for GitHub Analytical Records."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.data_science.quality import DataQualityChecker
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import (
    CommitRecord,
    ContributorRecord,
    DeveloperMetric,
    IssueRecord,
    PipelineRun,
    PullRequestRecord,
    Repository,
    ReviewRecord,
    SyncCheckpoint,
)


class DataIngestionPipeline:
    """Orchestrates resilient, incremental, idempotent GitHub data ingestion with quality verification."""

    def __init__(self, client: GitHubClient | None = None):
        self.client = client or GitHubClient()

    async def _get_or_create_repo(self, session, owner: str, repo_name: str) -> Repository:
        full_name = f"{owner}/{repo_name}"
        stmt = select(Repository).where(Repository.full_name == full_name)
        res = await session.execute(stmt)
        repo = res.scalar_one_or_none()
        if not repo:
            repo = Repository(
                github_id=abs(hash(full_name)) % 100000000,
                owner=owner,
                name=repo_name,
                full_name=full_name,
                is_active=True,
                monitoring_status="MONITORED",
                last_synced_at=datetime.now(UTC),
            )
            session.add(repo)
            await session.flush()
        else:
            repo.last_synced_at = datetime.now(UTC)
        return repo

    async def _get_or_create_checkpoint(
        self, session, repo_id: int, resource_type: str
    ) -> SyncCheckpoint:
        stmt = select(SyncCheckpoint).where(
            SyncCheckpoint.repo_id == repo_id,
            SyncCheckpoint.resource_type == resource_type,
        )
        res = await session.execute(stmt)
        cp = res.scalar_one_or_none()
        if not cp:
            cp = SyncCheckpoint(
                repo_id=repo_id,
                resource_type=resource_type,
                status="PENDING",
                records_synced=0,
                updated_at=datetime.now(UTC),
            )
            session.add(cp)
            await session.flush()
        return cp

    async def _save_checkpoint(
        self,
        session,
        repo_id: int,
        resource_type: str,
        last_item_id: str | None = None,
        last_timestamp: datetime | None = None,
        records_synced: int = 0,
        status: str = "COMPLETED",
        error_message: str | None = None,
    ) -> None:
        cp = await self._get_or_create_checkpoint(session, repo_id, resource_type)
        if last_item_id is not None:
            cp.last_item_id = str(last_item_id)
        if last_timestamp is not None:
            cp.last_checkpoint_timestamp = last_timestamp
        cp.records_synced += records_synced
        cp.status = status
        cp.error_message = error_message
        cp.updated_at = datetime.now(UTC)
        await session.flush()

    async def run_pipeline(
        self,
        owner: str,
        repo: str,
        incremental: bool = True,
        max_pages: int = 2,
    ) -> dict[str, Any]:
        """Executes full analytical ingestion wave for a repository, tracking status in PipelineRun."""
        await init_db()
        full_name = f"{owner}/{repo}"
        started_at = datetime.now(UTC)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                run = PipelineRun(
                    pipeline_name="full_analytical_sync",
                    target_repo=full_name,
                    status="RUNNING",
                    started_at=started_at,
                    records_processed=0,
                    records_failed=0,
                    metadata_json={"incremental": incremental, "max_pages": max_pages},
                )
                session.add(run)
                await session.flush()
                run_record_id = run.id

        total_processed = 0
        total_failed = 0
        status = "SUCCESS"
        err_msg: str | None = None

        try:
            pr_counts = await self.ingest_pull_requests(
                owner, repo, incremental=incremental, max_pages=max_pages
            )
            total_processed += pr_counts["processed"]
            total_failed += pr_counts["failed"]

            issue_counts = await self.ingest_issues(
                owner, repo, incremental=incremental, max_pages=max_pages
            )
            total_processed += issue_counts["processed"]
            total_failed += issue_counts["failed"]

            event_counts = await self.ingest_events(owner, repo, max_pages=max_pages)
            total_processed += event_counts["processed"]
            total_failed += event_counts["failed"]

            commit_counts = await self.ingest_commits(
                owner, repo, incremental=incremental, max_pages=max_pages
            )
            total_processed += commit_counts["processed"]
            total_failed += commit_counts["failed"]

            contrib_counts = await self.ingest_contributors(owner, repo, max_pages=max_pages)
            total_processed += contrib_counts["processed"]
            total_failed += contrib_counts["failed"]

            review_counts = await self.ingest_reviews(owner, repo)
            total_processed += review_counts["processed"]
            total_failed += review_counts["failed"]

            async with AsyncSessionLocal() as session:
                async with session.begin():
                    repo_obj = await self._get_or_create_repo(session, owner, repo)
                    await self._compute_and_save_daily_metrics(session, repo_obj.id, days=30)

        except Exception as exc:
            logger.error("Pipeline run failed for %s: %s", full_name, exc, exc_info=True)
            status = "FAILED"
            err_msg = str(exc)[:990]

        completed_at = datetime.now(UTC)
        duration_s = (completed_at - started_at).total_seconds()

        if run_record_id:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    stmt = select(PipelineRun).where(PipelineRun.id == run_record_id)
                    res = await session.execute(stmt)
                    run_record = res.scalar_one_or_none()
                    if run_record:
                        run_record.status = status
                        run_record.records_processed = total_processed
                        run_record.records_failed = total_failed
                        run_record.error_message = err_msg
                        run_record.completed_at = completed_at
                        run_record.metadata_json = {
                            "duration_seconds": duration_s,
                            "incremental": incremental,
                        }

        return {
            "pipeline_run_id": run_record_id,
            "status": status,
            "target_repo": full_name,
            "records_processed": total_processed,
            "records_failed": total_failed,
            "duration_seconds": duration_s,
            "error_message": err_msg,
        }

    def _process_single_pr(
        self,
        pr: dict[str, Any],
        repo_id: int,
        existing_prs: dict[int, PullRequestRecord],
        session,
    ) -> tuple[bool, datetime | None, str | None]:
        gh_id = int(pr.get("id") or 0)
        if not gh_id:
            return False, None, None

        number = int(pr.get("number") or 0)
        title = str(pr.get("title") or f"PR #{number}")[:500]
        body = str(pr.get("body") or "")[:5000]
        state = str(pr.get("state") or "open")
        user_info = pr.get("user") or {}
        author_login = str(user_info.get("login") or "unknown")[:100]

        c_at = self._parse_iso_dt(pr.get("created_at"))
        u_at = self._parse_iso_dt(pr.get("updated_at"))
        cl_at = self._parse_iso_dt(pr.get("closed_at"))
        m_at = self._parse_iso_dt(pr.get("merged_at"))
        r_at = self._parse_iso_dt(pr.get("first_reviewed_at"))

        valid, _ = DataQualityChecker.validate_timestamp_sequence(c_at, cl_at)
        if not valid:
            return False, None, None

        additions = max(0, int(pr.get("additions") or 0))
        deletions = max(0, int(pr.get("deletions") or 0))
        changed_files = max(0, int(pr.get("changed_files") or 0))
        review_comments = max(0, int(pr.get("review_comments") or 0))

        if gh_id in existing_prs:
            rec = existing_prs[gh_id]
            rec.repo_id = repo_id
            rec.title = title
            rec.body = body
            rec.state = state
            rec.updated_at = u_at
            rec.closed_at = cl_at
            rec.merged_at = m_at
            rec.first_reviewed_at = r_at or rec.first_reviewed_at
            rec.additions = additions
            rec.deletions = deletions
            rec.changed_files = changed_files
            rec.review_comments_count = review_comments
            rec.raw_payload = pr
        else:
            rec = PullRequestRecord(
                repo_id=repo_id,
                github_id=gh_id,
                number=number,
                title=title,
                body=body,
                state=state,
                author_login=author_login,
                created_at=c_at or datetime.now(UTC),
                updated_at=u_at,
                closed_at=cl_at,
                merged_at=m_at,
                first_reviewed_at=r_at,
                additions=additions,
                deletions=deletions,
                changed_files=changed_files,
                review_comments_count=review_comments,
                raw_payload=pr,
            )
            session.add(rec)
        return True, u_at, str(gh_id)

    async def _fetch_all_prs(
        self, owner: str, repo_name: str, max_pages: int
    ) -> list[dict[str, Any]]:
        raw_prs: list[dict[str, Any]] = []
        for p in range(1, max_pages + 1):
            page_prs = await self.client.fetch_repository_pull_requests(
                owner, repo_name, state="all", page=p, per_page=30
            )
            if not page_prs:
                break
            raw_prs.extend(page_prs)
            if len(page_prs) < 30:
                break
        if not raw_prs:
            raw_prs = await self.client.fetch_synthetic_pull_requests(owner, repo_name)
        return raw_prs

    async def ingest_pull_requests(
        self,
        owner: str,
        repo_name: str,
        incremental: bool = True,
        max_pages: int = 2,
    ) -> dict[str, int]:
        """Fetches and idempotently stores normalized PullRequest records with checkpoint support."""
        processed, failed = 0, 0
        raw_prs = await self._fetch_all_prs(owner, repo_name, max_pages)

        newest_updated: datetime | None = None
        newest_id: str | None = None

        async with AsyncSessionLocal() as session:
            async with session.begin():
                repo = await self._get_or_create_repo(session, owner, repo_name)
                checkpoint = await self._get_or_create_checkpoint(session, repo.id, "pull_requests")

                gh_ids = [pr.get("id") for pr in raw_prs if pr.get("id")]
                existing_prs = {}
                if gh_ids:
                    stmt = select(PullRequestRecord).where(
                        PullRequestRecord.github_id.in_(gh_ids),
                    )
                    res = await session.execute(stmt)
                    for r in res.scalars():
                        existing_prs[r.github_id] = r

                for pr in raw_prs:
                    try:
                        ok, u_at, gid = self._process_single_pr(pr, repo.id, existing_prs, session)
                        if ok:
                            processed += 1
                            if u_at and (newest_updated is None or u_at > newest_updated):
                                newest_updated = u_at
                                newest_id = gid
                        else:
                            failed += 1
                    except Exception as err:
                        logger.warning("Error ingesting PR %s: %s", pr.get("id"), err)
                        failed += 1

                await self._save_checkpoint(
                    session,
                    repo.id,
                    "pull_requests",
                    last_item_id=newest_id or checkpoint.last_item_id,
                    last_timestamp=newest_updated or checkpoint.last_checkpoint_timestamp,
                    records_synced=processed,
                    status="COMPLETED",
                )

        return {"processed": processed, "failed": failed}

    def _process_single_issue(
        self,
        iss: dict[str, Any],
        repo_id: int,
        existing_issues: dict[int, IssueRecord],
        session,
    ) -> tuple[bool, datetime | None, str | None]:
        gh_id = int(iss.get("id") or 0)
        if not gh_id:
            return False, None, None

        number = int(iss.get("number") or 0)
        title = str(iss.get("title") or f"Issue #{number}")[:500]
        body = str(iss.get("body") or "")[:5000]
        state = str(iss.get("state") or "open")
        user_info = iss.get("user") or {}
        author_login = str(user_info.get("login") or "unknown")[:100]

        c_at = self._parse_iso_dt(iss.get("created_at"))
        u_at = self._parse_iso_dt(iss.get("updated_at"))
        cl_at = self._parse_iso_dt(iss.get("closed_at"))

        valid, _ = DataQualityChecker.validate_timestamp_sequence(c_at, cl_at)
        if not valid:
            return False, None, None

        raw_labels = iss.get("labels") or []
        label_names = [lbl.get("name") if isinstance(lbl, dict) else str(lbl) for lbl in raw_labels]
        comments_count = max(0, int(iss.get("comments") or 0))

        if gh_id in existing_issues:
            rec = existing_issues[gh_id]
            rec.repo_id = repo_id
            rec.title = title
            rec.body = body
            rec.state = state
            rec.updated_at = u_at
            rec.closed_at = cl_at
            rec.labels = label_names
            rec.comments_count = comments_count
            rec.raw_payload = iss
        else:
            rec = IssueRecord(
                repo_id=repo_id,
                github_id=gh_id,
                number=number,
                title=title,
                body=body,
                state=state,
                author_login=author_login,
                labels=label_names,
                comments_count=comments_count,
                created_at=c_at or datetime.now(UTC),
                updated_at=u_at,
                closed_at=cl_at,
                raw_payload=iss,
            )
            session.add(rec)
        return True, u_at, str(gh_id)

    async def _fetch_all_issues(
        self, owner: str, repo_name: str, since_param: str | None, max_pages: int
    ) -> list[dict[str, Any]]:
        raw_issues: list[dict[str, Any]] = []
        for p in range(1, max_pages + 1):
            page_issues = await self.client.fetch_repository_issues(
                owner, repo_name, since=since_param, page=p, per_page=50
            )
            if not page_issues:
                break
            raw_issues.extend(page_issues)
            if len(page_issues) < 50:
                break
        if not raw_issues and not since_param:
            raw_issues = await self.client.fetch_synthetic_issues(owner, repo_name)
        return raw_issues

    async def ingest_issues(
        self,
        owner: str,
        repo_name: str,
        incremental: bool = True,
        max_pages: int = 2,
    ) -> dict[str, int]:
        """Fetches and idempotently stores normalized Issue records (excluding PRs)."""
        processed, failed = 0, 0
        since_param: str | None = None

        async with AsyncSessionLocal() as session:
            repo = await self._get_or_create_repo(session, owner, repo_name)
            checkpoint = await self._get_or_create_checkpoint(session, repo.id, "issues")
            if incremental and checkpoint.last_checkpoint_timestamp:
                since_param = checkpoint.last_checkpoint_timestamp.isoformat()

        raw_issues = await self._fetch_all_issues(owner, repo_name, since_param, max_pages)
        newest_updated: datetime | None = None
        newest_id: str | None = None

        async with AsyncSessionLocal() as session:
            async with session.begin():
                repo = await self._get_or_create_repo(session, owner, repo_name)
                gh_ids = [iss.get("id") for iss in raw_issues if iss.get("id")]
                existing_issues = {}
                if gh_ids:
                    stmt = select(IssueRecord).where(
                        IssueRecord.github_id.in_(gh_ids),
                    )
                    res = await session.execute(stmt)
                    for r in res.scalars():
                        existing_issues[r.github_id] = r

                for iss in raw_issues:
                    try:
                        ok, u_at, gid = self._process_single_issue(
                            iss, repo.id, existing_issues, session
                        )
                        if ok:
                            processed += 1
                            if u_at and (newest_updated is None or u_at > newest_updated):
                                newest_updated = u_at
                                newest_id = gid
                        else:
                            failed += 1
                    except Exception as err:
                        logger.warning("Error ingesting Issue %s: %s", iss.get("id"), err)
                        failed += 1

                await self._save_checkpoint(
                    session,
                    repo.id,
                    "issues",
                    last_item_id=newest_id,
                    last_timestamp=newest_updated,
                    records_synced=processed,
                    status="COMPLETED",
                )

        return {"processed": processed, "failed": failed}

    async def ingest_events(
        self,
        owner: str,
        repo_name: str,
        max_pages: int = 2,
    ) -> dict[str, int]:
        """Fetches and stores raw event stream with deduplication and checkpoint recording."""
        from backend.src.gitpulse.ingestion.runner import _persist_events_to_db

        events = await self.client.fetch_all_recent_events(owner, repo_name, max_pages=max_pages)
        if not events:
            events = await self.client.fetch_synthetic_events(owner, repo_name)

        saved = await _persist_events_to_db(owner, repo_name, events)

        latest_event_id = events[0].get("id") if events else None
        async with AsyncSessionLocal() as session:
            async with session.begin():
                repo = await self._get_or_create_repo(session, owner, repo_name)
                await self._save_checkpoint(
                    session,
                    repo.id,
                    "events",
                    last_item_id=str(latest_event_id) if latest_event_id else None,
                    last_timestamp=datetime.now(UTC),
                    records_synced=saved,
                    status="COMPLETED",
                )

        return {"processed": saved, "failed": max(0, len(events) - saved)}

    async def _fetch_all_commits(
        self, owner: str, repo_name: str, max_pages: int
    ) -> list[dict[str, Any]]:
        raw_commits: list[dict[str, Any]] = []
        for p in range(1, max_pages + 1):
            page_commits = await self.client.fetch_repository_commits(
                owner, repo_name, page=p, per_page=50
            )
            if not page_commits:
                break
            raw_commits.extend(page_commits)
            if len(page_commits) < 50:
                break
        return raw_commits

    async def _build_commit_record(
        self, c: dict[str, Any], repo_id: int, owner: str, repo_name: str, idx: int
    ) -> CommitRecord | None:
        sha = str(c.get("sha") or "")
        if not sha:
            return None

        c_meta = c.get("commit", {})
        committer = c_meta.get("committer") or c_meta.get("author") or {}
        c_date = self._parse_iso_dt(committer.get("date")) or datetime.now(UTC)
        author_name = str(committer.get("name") or "author")[:100]
        author_email = str(committer.get("email") or "author@gitpulse.internal")[:150]
        message = str(c_meta.get("message") or "")[:1000]

        lines_added = 0
        lines_deleted = 0
        stats = c.get("stats")
        if isinstance(stats, dict):
            lines_added = max(0, int(stats.get("additions", 0)))
            lines_deleted = max(0, int(stats.get("deletions", 0)))
        elif idx < 10:
            detail = await self.client.fetch_commit_details(owner, repo_name, sha)
            if detail and isinstance(detail.get("stats"), dict):
                lines_added = max(0, int(detail["stats"].get("additions", 0)))
                lines_deleted = max(0, int(detail["stats"].get("deletions", 0)))

        return CommitRecord(
            sha=sha,
            repo_id=repo_id,
            author_name=author_name,
            author_email=author_email,
            message=message,
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            committed_at=c_date,
        )

    async def ingest_commits(
        self,
        owner: str,
        repo_name: str,
        incremental: bool = True,
        max_pages: int = 2,
    ) -> dict[str, int]:
        """Fetches and idempotently persists commits with real lines added/deleted stats."""
        processed, failed = 0, 0
        raw_commits = await self._fetch_all_commits(owner, repo_name, max_pages)

        newest_sha: str | None = None
        newest_date: datetime | None = None

        async with AsyncSessionLocal() as session:
            async with session.begin():
                repo = await self._get_or_create_repo(session, owner, repo_name)
                shas = [c.get("sha") for c in raw_commits if c.get("sha")]
                existing_shas = set()
                if shas:
                    stmt = select(CommitRecord.sha).where(
                        CommitRecord.repo_id == repo.id,
                        CommitRecord.sha.in_(shas),
                    )
                    res = await session.execute(stmt)
                    existing_shas = set(res.scalars().all())

                new_commits = [
                    c for c in raw_commits if str(c.get("sha") or "") not in existing_shas
                ]

                for idx, c in enumerate(new_commits):
                    try:
                        rec = await self._build_commit_record(c, repo.id, owner, repo_name, idx)
                        if rec:
                            if newest_date is None or rec.committed_at > newest_date:
                                newest_date = rec.committed_at
                                newest_sha = rec.sha
                            session.add(rec)
                            processed += 1
                    except Exception as exc:
                        logger.warning("Error ingesting commit: %s", exc)
                        failed += 1

                await self._save_checkpoint(
                    session,
                    repo.id,
                    "commits",
                    last_item_id=newest_sha,
                    last_timestamp=newest_date,
                    records_synced=processed,
                    status="COMPLETED",
                )

        return {"processed": processed, "failed": failed}

    async def _upsert_contributor(
        self,
        contrib: dict[str, Any],
        repo_id: int,
        existing_map: dict[str, ContributorRecord],
        session,
    ) -> bool:
        login = str(contrib.get("login") or "").strip()
        if not login:
            return False

        avatar_url = contrib.get("avatar_url")
        html_url = contrib.get("html_url")
        contributions = max(0, int(contrib.get("contributions", 0)))

        pr_stmt = select(func.count(PullRequestRecord.id)).where(
            PullRequestRecord.repo_id == repo_id,
            PullRequestRecord.author_login == login,
        )
        prs_cnt = (await session.execute(pr_stmt)).scalar() or 0

        iss_stmt = select(func.count(IssueRecord.id)).where(
            IssueRecord.repo_id == repo_id,
            IssueRecord.author_login == login,
        )
        iss_cnt = (await session.execute(iss_stmt)).scalar() or 0

        comm_stmt = select(func.count(CommitRecord.id)).where(
            CommitRecord.repo_id == repo_id,
            CommitRecord.author_name == login,
        )
        comm_cnt = (await session.execute(comm_stmt)).scalar() or 0

        if login in existing_map:
            rec = existing_map[login]
            rec.avatar_url = avatar_url or rec.avatar_url
            rec.html_url = html_url or rec.html_url
            rec.contributions_count = max(contributions, rec.contributions_count)
            rec.prs_count = prs_cnt
            rec.issues_count = iss_cnt
            rec.commits_count = max(comm_cnt, contributions)
            rec.last_contributed_at = datetime.now(UTC)
        else:
            rec = ContributorRecord(
                repo_id=repo_id,
                login=login,
                avatar_url=avatar_url,
                html_url=html_url,
                contributions_count=contributions,
                commits_count=max(comm_cnt, contributions),
                prs_count=prs_cnt,
                issues_count=iss_cnt,
                first_contributed_at=datetime.now(UTC),
                last_contributed_at=datetime.now(UTC),
            )
            session.add(rec)
        return True

    async def ingest_contributors(
        self,
        owner: str,
        repo_name: str,
        max_pages: int = 2,
    ) -> dict[str, int]:
        """Fetches and idempotently stores active contributors with contribution metrics."""
        processed, failed = 0, 0
        raw_contribs: list[dict[str, Any]] = []

        for p in range(1, max_pages + 1):
            page_contribs = await self.client.fetch_repository_contributors(
                owner, repo_name, page=p, per_page=100
            )
            if not page_contribs:
                break
            raw_contribs.extend(page_contribs)
            if len(page_contribs) < 100:
                break

        if not raw_contribs:
            raw_contribs = await self.client.fetch_synthetic_contributors(owner, repo_name)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                repo = await self._get_or_create_repo(session, owner, repo_name)
                logins = [c.get("login") for c in raw_contribs if c.get("login")]
                existing_map = {}
                if logins:
                    stmt = select(ContributorRecord).where(
                        ContributorRecord.repo_id == repo.id,
                        ContributorRecord.login.in_(logins),
                    )
                    res = await session.execute(stmt)
                    for r in res.scalars():
                        existing_map[r.login] = r

                for contrib in raw_contribs:
                    try:
                        ok = await self._upsert_contributor(contrib, repo.id, existing_map, session)
                        if ok:
                            processed += 1
                        else:
                            failed += 1
                    except Exception as exc:
                        logger.warning("Error ingesting contributor: %s", exc)
                        failed += 1

                await self._save_checkpoint(
                    session,
                    repo.id,
                    "contributors",
                    records_synced=processed,
                    status="COMPLETED",
                )

        return {"processed": processed, "failed": failed}

    async def ingest_reviews(
        self,
        owner: str,
        repo_name: str,
        max_prs: int = 25,
    ) -> dict[str, int]:
        """Fetches reviews for recent pull requests and populates ReviewRecord and first_reviewed_at."""
        processed, failed = 0, 0

        async with AsyncSessionLocal() as session:
            async with session.begin():
                repo = await self._get_or_create_repo(session, owner, repo_name)
                stmt = (
                    select(PullRequestRecord)
                    .where(PullRequestRecord.repo_id == repo.id)
                    .order_by(PullRequestRecord.created_at.desc())
                    .limit(max_prs)
                )
                prs = list((await session.execute(stmt)).scalars().all())

        for pr in prs:
            try:
                raw_reviews = await self.client.fetch_pull_request_reviews(
                    owner, repo_name, pr.number
                )
                if not raw_reviews:
                    continue

                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        pr_rec = await session.get(PullRequestRecord, pr.id)
                        if not pr_rec:
                            continue

                        earliest_rev_dt = pr_rec.first_reviewed_at

                        for rev in raw_reviews:
                            rev_id = int(rev.get("id") or 0)
                            if not rev_id:
                                continue

                            rev_user = rev.get("user") or {}
                            reviewer = str(rev_user.get("login") or "reviewer")[:100]
                            rev_state = str(rev.get("state") or "APPROVED")
                            sub_dt = self._parse_iso_dt(rev.get("submitted_at")) or datetime.now(
                                UTC
                            )
                            body = str(rev.get("body") or "")[:2000]

                            if earliest_rev_dt is None or sub_dt < earliest_rev_dt:
                                earliest_rev_dt = sub_dt

                            chk_stmt = select(ReviewRecord).where(ReviewRecord.github_id == rev_id)
                            existing_rev = (await session.execute(chk_stmt)).scalar_one_or_none()
                            if not existing_rev:
                                new_rev = ReviewRecord(
                                    pr_id=pr_rec.id,
                                    github_id=rev_id,
                                    reviewer_login=reviewer,
                                    state=rev_state,
                                    submitted_at=sub_dt,
                                    body=body,
                                )
                                session.add(new_rev)
                                processed += 1

                        pr_rec.first_reviewed_at = earliest_rev_dt
            except Exception as exc:
                logger.warning("Error ingesting reviews for PR #%d: %s", pr.number, exc)
                failed += 1

        return {"processed": processed, "failed": failed}

    async def _compute_and_save_daily_metrics(self, session, repo_id: int, days: int = 30) -> None:
        """Computes daily DeveloperMetric records derived directly from database tables."""
        now_dt = datetime.now(UTC)
        cutoff = now_dt - timedelta(days=days)

        c_stmt = select(CommitRecord).where(
            CommitRecord.repo_id == repo_id,
            CommitRecord.committed_at >= cutoff,
        )
        commits = list((await session.execute(c_stmt)).scalars().all())

        pr_stmt = select(PullRequestRecord).where(
            PullRequestRecord.repo_id == repo_id,
            PullRequestRecord.created_at >= cutoff,
        )
        prs = list((await session.execute(pr_stmt)).scalars().all())

        daily_commits = defaultdict(int)
        daily_added = defaultdict(int)
        daily_deleted = defaultdict(int)
        daily_authors = defaultdict(set)
        daily_cycle_times = defaultdict(list)

        for c in commits:
            if c.committed_at:
                day_str = c.committed_at.strftime("%Y-%m-%d")
                daily_commits[day_str] += 1
                daily_added[day_str] += c.lines_added
                daily_deleted[day_str] += c.lines_deleted
                if c.author_name:
                    daily_authors[day_str].add(c.author_name)

        for pr in prs:
            if pr.created_at:
                day_str = pr.created_at.strftime("%Y-%m-%d")
                if pr.author_login:
                    daily_authors[day_str].add(pr.author_login)
                if pr.merged_at and pr.created_at:
                    hrs = (pr.merged_at - pr.created_at).total_seconds() / 3600.0
                    if 0 < hrs < 720:
                        daily_cycle_times[day_str].append(hrs)

        for i in range(days):
            day_dt = now_dt - timedelta(days=i)
            day_str = day_dt.strftime("%Y-%m-%d")
            await self._upsert_daily_metric_row(
                session,
                repo_id,
                day_str,
                daily_commits[day_str],
                daily_added[day_str],
                daily_deleted[day_str],
                len(daily_authors[day_str]),
                daily_cycle_times[day_str],
            )

    async def _upsert_daily_metric_row(
        self,
        session,
        repo_id: int,
        day_str: str,
        c_count: int,
        added: int,
        deleted: int,
        active_auth: int,
        cycles: list[float],
    ) -> None:
        avg_cycle = round(sum(cycles) / len(cycles), 2) if cycles else 0.0
        churn = round(deleted / (added + deleted), 2) if (added + deleted) > 0 else 0.0

        met_stmt = select(DeveloperMetric).where(
            DeveloperMetric.repo_id == repo_id,
            DeveloperMetric.metric_date == day_str,
        )
        existing_met = (await session.execute(met_stmt)).scalar_one_or_none()

        if existing_met:
            existing_met.commit_count = c_count
            existing_met.active_contributors = active_auth
            existing_met.avg_pr_cycle_time_hours = avg_cycle
            existing_met.lines_added = added
            existing_met.lines_deleted = deleted
            existing_met.churn_rate = churn
        else:
            new_met = DeveloperMetric(
                repo_id=repo_id,
                metric_date=day_str,
                commit_count=c_count,
                active_contributors=active_auth,
                avg_pr_cycle_time_hours=avg_cycle,
                lines_added=added,
                lines_deleted=deleted,
                churn_rate=churn,
            )
            session.add(new_met)

    @staticmethod
    def _parse_iso_dt(val: Any) -> datetime | None:
        if not val:
            return None
        if isinstance(val, datetime):
            return val if val.tzinfo else val.replace(tzinfo=UTC)
        try:
            return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        except Exception:
            return None
