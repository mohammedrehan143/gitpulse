"""FastAPI Route Definitions for GitPulse Analytics Platform."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.src.gitpulse.api.schemas import (
    AIGenerateRequest,
    AIGenerateResponse,
    AIInsightsResponse,
    ContributorItem,
    ContributorsResponse,
    DiscoveredRepositoryItem,
    EventItem,
    EventsResponse,
    HealthResponse,
    IssueItem,
    IssuesResponse,
    KeepAliveResponse,
    PullRequestItem,
    PullRequestsResponse,
    ReconciliationResponse,
    RefreshRepositoriesResponse,
    RepositoriesResponse,
    RepositoryRef,
    RepoStatsResponse,
    RepoSubscribersResponse,
    SubscribeRepoRequest,
    SubscribeRepoResponse,
    SubscriberItem,
    SyncCheckpointItem,
    SyncRepositoryResponse,
    TimelinePoint,
    UniversalCommitNotificationRequest,
    UniversalCommitNotificationResponse,
    UniversalPullNotificationRequest,
    UniversalPullNotificationResponse,
    UniversalPushNotificationRequest,
    UniversalPushNotificationResponse,
    UnsubscribeRepoRequest,
    UnsubscribeRepoResponse,
    VelocityResponse,
    VelocitySummary,
)
from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.ingestion.pipeline import DataIngestionPipeline
from backend.src.gitpulse.ingestion.runner import _persist_events_to_db
from backend.src.gitpulse.services.ai_service import AIServiceException, GroqAIService
from backend.src.gitpulse.services.notification_service import NotificationService
from backend.src.gitpulse.services.reconciliation_service import DataReconciliationService
from backend.src.gitpulse.services.repository_service import RepositoryService
from backend.src.gitpulse.services.subscription_service import subscription_service
from backend.src.gitpulse.services.webhook_service import webhook_service
from backend.src.gitpulse.storage.database import AsyncSessionLocal
from backend.src.gitpulse.storage.models import (
    CommitRecord,
    ContributorRecord,
    GitHubEvent,
    IssueRecord,
    PullRequestRecord,
    Repository,
    SyncCheckpoint,
)

router = APIRouter(prefix="/api/v1", tags=["analytics"])


class WebSocketConnectionManager:
    """Manages active WebSocket subscriptions for real-time repo activity."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, repo_key: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[repo_key].append(websocket)
        logger.info("WebSocket client connected to %s", repo_key)

    def disconnect(self, repo_key: str, websocket: WebSocket) -> None:
        if websocket in self.active_connections[repo_key]:
            self.active_connections[repo_key].remove(websocket)
            logger.info("WebSocket client disconnected from %s", repo_key)

    async def broadcast(self, repo_key: str, message: dict[str, Any]) -> None:
        for connection in list(self.active_connections.get(repo_key, [])):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(repo_key, connection)


ws_manager = WebSocketConnectionManager()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Service health and operational status."""
    return HealthResponse(
        status="HEALTHY",
        version="0.1.0",
        environment=settings.GITPULSE_ENV,
    )


@router.get("/keepalive", response_model=KeepAliveResponse)
@router.post("/keepalive", response_model=KeepAliveResponse)
async def keep_alive_heartbeat(
    source: str = Query("external", description="Source of keep-alive request"),
    sync: bool = Query(False, description="Whether to trigger an on-demand database sync"),
) -> KeepAliveResponse:
    """Automated keep-alive endpoint that touches the database and refreshes sync state every 5 minutes."""
    from backend.src.gitpulse.services.keep_alive_service import keep_alive_service

    result = await keep_alive_service.execute_pulse_check(source=source, trigger_sync=sync)
    return KeepAliveResponse(**result)


@router.get("/repos", response_model=RepositoriesResponse)
async def list_repositories() -> RepositoriesResponse:
    """Lists all discovered repositories and their monitoring status."""
    service = RepositoryService()
    repos = await service.get_all_repositories()
    items = []
    for r in repos:
        rc = dict(r)
        if not rc.get("github_id"):
            rc["github_id"] = rc.get("id") or 0
        items.append(DiscoveredRepositoryItem(**rc))
    return RepositoriesResponse(
        total_count=len(items),
        auto_discover_enabled=settings.AUTO_DISCOVER_REPOSITORIES,
        repositories=items,
    )


@router.post("/repos/refresh", response_model=RefreshRepositoriesResponse)
async def refresh_repositories() -> RefreshRepositoriesResponse:
    """Triggers an on-demand synchronization and discovery of repositories."""
    service = RepositoryService()
    synced = await service.sync_repositories()
    items = []
    for r in synced:
        rc = dict(r)
        if not rc.get("github_id"):
            rc["github_id"] = rc.get("id") or 0
        items.append(DiscoveredRepositoryItem(**rc))
    return RefreshRepositoriesResponse(
        status="SYNCHRONIZED",
        synced_count=len(items),
        repositories=items,
    )


def _normalize_utc_dt(dt: datetime | None) -> datetime | None:
    """Normalizes any datetime (offset-naive or offset-aware) to UTC timezone-aware datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@router.post("/ai/generate", response_model=AIGenerateResponse)
async def ai_generate(request: AIGenerateRequest) -> AIGenerateResponse:
    """Direct invocation of Groq LLM inference for velocity or architecture tasks."""
    service = GroqAIService(model=request.model)
    try:
        response_text = service.generate_completion(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
        )
    except AIServiceException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return AIGenerateResponse(
        model=request.model or service.model,
        response=response_text,
    )


async def _verify_repository_exists_for_ai(
    owner: str,
    repo: str,
    full_name: str,
    correlation_id: str,
) -> None:
    """Ensures repository exists in DB or can be discovered on GitHub before AI analysis."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(Repository).where(Repository.full_name == full_name)
            res = await session.execute(stmt)
            repo_obj = res.scalar_one_or_none()

        if not repo_obj:
            repo_service = RepositoryService()
            meta = await repo_service.client.fetch_repository_metadata(owner, repo)
            if not meta:
                logger.warning(
                    "[%s] Repository %s not found in database or GitHub", correlation_id, full_name
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Repository '{full_name}' not found",
                    headers={"X-Correlation-ID": correlation_id},
                )
            await repo_service.ensure_repository_tracked(owner, repo)
    except HTTPException:
        raise
    except (SQLAlchemyError, ConnectionError, OSError) as db_exc:
        logger.error(
            "[%s] Database error verifying repository %s: %s", correlation_id, full_name, db_exc
        )
        raise HTTPException(
            status_code=503,
            detail="Database service temporarily unavailable. Please retry shortly.",
            headers={"X-Correlation-ID": correlation_id},
        ) from db_exc
    except Exception as exc:
        logger.error(
            "[%s] Unexpected error verifying repository %s: %s",
            correlation_id,
            full_name,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected internal error occurred (ID: {correlation_id})",
            headers={"X-Correlation-ID": correlation_id},
        ) from exc


async def _retrieve_velocity_summary(
    owner: str,
    repo: str,
    full_name: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Retrieves 30-day velocity metrics dictionary with error handling."""
    try:
        velocity_data = await get_repository_velocity(
            owner=owner,
            repo=repo,
            timeframe="30d",
            granularity="day",
        )
    except HTTPException:
        raise
    except SQLAlchemyError as db_exc:
        logger.error(
            "[%s] Database query failure fetching velocity for %s: %s",
            correlation_id,
            full_name,
            db_exc,
        )
        raise HTTPException(
            status_code=500,
            detail="Database query failed while calculating repository velocity metrics.",
            headers={"X-Correlation-ID": correlation_id},
        ) from db_exc
    except Exception as exc:
        logger.error(
            "[%s] Failed to calculate velocity for %s: %s",
            correlation_id,
            full_name,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected internal error occurred while calculating repository metrics (ID: {correlation_id})",
            headers={"X-Correlation-ID": correlation_id},
        ) from exc

    return {
        "total_commits": velocity_data.summary.total_commits,
        "active_contributors": velocity_data.summary.active_contributors,
        "avg_pr_cycle_time_hours": velocity_data.summary.avg_pr_cycle_time_hours,
        "churn_rate": velocity_data.summary.churn_rate,
        "lines_added": velocity_data.summary.lines_added,
        "lines_deleted": velocity_data.summary.lines_deleted,
    }


def _generate_ai_velocity_insights(
    service: GroqAIService,
    full_name: str,
    summary_dict: dict[str, Any],
    correlation_id: str,
) -> str:
    """Executes Groq AI metrics analysis with typed exception handling."""
    try:
        return service.analyze_repository_metrics(
            repo_full_name=full_name,
            metrics=summary_dict,
        )
    except AIServiceException as ai_exc:
        logger.error(
            "[%s] AI service error for %s: [%s] %s",
            correlation_id,
            full_name,
            ai_exc.category,
            ai_exc.message,
        )
        raise HTTPException(
            status_code=ai_exc.status_code,
            detail=f"{ai_exc.message} (ID: {correlation_id})",
            headers={"X-Correlation-ID": correlation_id},
        ) from ai_exc
    except Exception as exc:
        logger.error(
            "[%s] Unexpected exception during AI analysis for %s: %s",
            correlation_id,
            full_name,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected internal error occurred during AI analysis (ID: {correlation_id})",
            headers={"X-Correlation-ID": correlation_id},
        ) from exc


@router.post("/repos/{owner}/{repo}/ai-insights", response_model=AIInsightsResponse)
async def get_repository_ai_insights(
    owner: str,
    repo: str,
    request: Request,
) -> AIInsightsResponse:
    """Produces AI velocity and architecture insights for a repository using Groq."""
    correlation_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    full_name = f"{owner}/{repo}"
    logger.info("[%s] Generating AI insights for repository: %s", correlation_id, full_name)

    await _verify_repository_exists_for_ai(owner, repo, full_name, correlation_id)
    summary_dict = await _retrieve_velocity_summary(owner, repo, full_name, correlation_id)

    service = GroqAIService()
    insights = _generate_ai_velocity_insights(service, full_name, summary_dict, correlation_id)

    return AIInsightsResponse(
        repository=full_name,
        model=service.model,
        insights=insights,
    )


def _generate_timeline_buckets(
    days: int,
    granularity: str,
    daily_commits: dict[str, int],
    daily_prs_opened: dict[str, int],
    daily_prs_merged: dict[str, int],
    daily_authors: dict[str, set[str]],
    daily_lines: dict[str, int],
) -> list[TimelinePoint]:
    points_count = min(days if granularity == "day" else max(days // 7, 1), 30)
    timeline_points: list[TimelinePoint] = []
    now_dt = datetime.now(UTC)

    for i in range(points_count - 1, -1, -1):
        day_str = (now_dt - timedelta(days=i)).strftime("%Y-%m-%d")
        c_count = daily_commits.get(day_str, 0)
        timeline_points.append(
            TimelinePoint(
                timestamp=f"{day_str}T00:00:00Z",
                commit_count=c_count,
                pr_opened_count=daily_prs_opened.get(day_str, 0),
                pr_merged_count=daily_prs_merged.get(day_str, 0),
                active_authors=len(daily_authors.get(day_str, set())),
                net_lines=daily_lines.get(day_str, 0),
            )
        )
    return timeline_points


async def _fetch_and_aggregate_commits(
    session,
    repo_id: int,
    cutoff: datetime,
    owner: str,
    repo: str,
    daily_commits: dict[str, int],
    daily_lines: dict[str, int],
    daily_authors: dict[str, set[str]],
) -> tuple[int, int]:
    c_stmt = select(CommitRecord).where(
        CommitRecord.repo_id == repo_id,
        CommitRecord.committed_at >= cutoff,
    )
    commits = list((await session.execute(c_stmt)).scalars().all())

    # If 0 commits in DB, backfill 1 page of commits & PRs on first connect
    if not commits:
        try:
            pipeline = DataIngestionPipeline()
            await pipeline.ingest_commits(owner, repo, incremental=False, max_pages=1)
            commits = list((await session.execute(c_stmt)).scalars().all())
        except Exception as exc:
            logger.debug("Initial backfill skipped: %s", exc)

    total_added, total_deleted = 0, 0
    for c in commits:
        c_utc = _normalize_utc_dt(c.committed_at)
        if c_utc:
            c_day = c_utc.strftime("%Y-%m-%d")
            daily_commits[c_day] += 1
            daily_lines[c_day] += c.lines_added
            total_added += c.lines_added
            total_deleted += c.lines_deleted
            if c.author_name:
                daily_authors[c_day].add(c.author_name)
    return total_added, total_deleted


async def _fetch_and_aggregate_prs(
    session,
    repo_id: int,
    cutoff: datetime,
    owner: str,
    repo: str,
    daily_prs_opened: dict[str, int],
    daily_prs_merged: dict[str, int],
    daily_authors: dict[str, set[str]],
) -> list[float]:
    pr_stmt = select(PullRequestRecord).where(
        PullRequestRecord.repo_id == repo_id,
        PullRequestRecord.created_at >= cutoff,
    )
    prs = list((await session.execute(pr_stmt)).scalars().all())
    if not prs:
        try:
            pipeline = DataIngestionPipeline()
            await pipeline.ingest_pull_requests(owner, repo, incremental=False, max_pages=1)
            prs = list((await session.execute(pr_stmt)).scalars().all())
        except Exception as exc:
            logger.debug("Initial PR backfill skipped: %s", exc)

    cycle_times: list[float] = []
    cutoff_utc = _normalize_utc_dt(cutoff) or cutoff
    for pr in prs:
        created_utc = _normalize_utc_dt(pr.created_at)
        merged_utc = _normalize_utc_dt(pr.merged_at)
        if created_utc:
            p_day = created_utc.strftime("%Y-%m-%d")
            daily_prs_opened[p_day] += 1
            if pr.author_login:
                daily_authors[p_day].add(pr.author_login)
        if merged_utc and merged_utc >= cutoff_utc:
            m_day = merged_utc.strftime("%Y-%m-%d")
            daily_prs_merged[m_day] += 1
            if created_utc:
                hrs = (merged_utc - created_utc).total_seconds() / 3600.0
                if 0 < hrs < 720:
                    cycle_times.append(hrs)
    return cycle_times


@router.get("/repos/{owner}/{repo}/velocity", response_model=VelocityResponse)
async def get_repository_velocity(
    owner: str,
    repo: str,
    timeframe: str = Query("30d", pattern="^(7d|14d|30d|90d|1y)$"),
    granularity: str = Query("day", pattern="^(hour|day|week)$"),
) -> VelocityResponse:
    """Retrieves real aggregated commit velocity and cycle time metrics from database."""
    full_name = f"{owner}/{repo}"
    repo_service = RepositoryService()
    repo_info = await repo_service.ensure_repository_tracked(owner, repo)

    multiplier_map = {"7d": 7, "14d": 14, "30d": 30, "90d": 90, "1y": 365}
    days = multiplier_map.get(timeframe, 30)
    cutoff = datetime.now(UTC) - timedelta(days=days)

    daily_commits: dict[str, int] = defaultdict(int)
    daily_prs_opened: dict[str, int] = defaultdict(int)
    daily_prs_merged: dict[str, int] = defaultdict(int)
    daily_authors: dict[str, set[str]] = defaultdict(set)
    daily_lines: dict[str, int] = defaultdict(int)
    cycle_times: list[float] = []
    total_added = 0
    total_deleted = 0

    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == full_name)
        res = await session.execute(stmt)
        repo_obj = res.scalar_one_or_none()
        repo_id = repo_obj.id if repo_obj else None

        if repo_id:
            total_added, total_deleted = await _fetch_and_aggregate_commits(
                session, repo_id, cutoff, owner, repo, daily_commits, daily_lines, daily_authors
            )
            cycle_times = await _fetch_and_aggregate_prs(
                session,
                repo_id,
                cutoff,
                owner,
                repo,
                daily_prs_opened,
                daily_prs_merged,
                daily_authors,
            )

            # Also check raw events for contributor activities
            evt_stmt = select(GitHubEvent).where(
                GitHubEvent.repo_id == repo_id,
                GitHubEvent.created_at >= cutoff,
            )
            events = list((await session.execute(evt_stmt)).scalars().all())
            for e in events:
                e_utc = _normalize_utc_dt(e.created_at)
                if e_utc and e.actor_login:
                    e_day = e_utc.strftime("%Y-%m-%d")
                    daily_authors[e_day].add(e.actor_login)

    timeline_points = _generate_timeline_buckets(
        days,
        granularity,
        daily_commits,
        daily_prs_opened,
        daily_prs_merged,
        daily_authors,
        daily_lines,
    )

    total_commits = sum(p.commit_count for p in timeline_points)
    all_authors: set[str] = set()
    for s in daily_authors.values():
        all_authors.update(s)
    active_contributors = len(all_authors)

    churn = (
        round(total_deleted / (total_added + total_deleted), 2)
        if (total_added + total_deleted) > 0
        else 0.0
    )
    avg_cycle = round(sum(cycle_times) / len(cycle_times), 1) if cycle_times else 0.0

    return VelocityResponse(
        repository=RepositoryRef(
            id=repo_info.get("id") or repo_info.get("github_id") or 1,
            owner=owner,
            name=repo,
            full_name=full_name,
        ),
        timeframe=timeframe,
        granularity=granularity,
        summary=VelocitySummary(
            total_commits=total_commits,
            active_contributors=active_contributors,
            avg_pr_cycle_time_hours=avg_cycle,
            lines_added=total_added,
            lines_deleted=total_deleted,
            churn_rate=churn,
        ),
        timeline=timeline_points,
    )


@router.get("/repos/{owner}/{repo}/stats", response_model=RepoStatsResponse)
async def get_repository_stats(owner: str, repo: str) -> RepoStatsResponse:
    """Retrieves full repository statistics, activity counters, and synchronization checkpoints."""
    full_name = f"{owner}/{repo}"
    repo_service = RepositoryService()
    await repo_service.ensure_repository_tracked(owner, repo)

    async with AsyncSessionLocal() as session:
        repo_obj = (
            await session.execute(select(Repository).where(Repository.full_name == full_name))
        ).scalar_one_or_none()
        if not repo_obj:
            raise HTTPException(status_code=404, detail=f"Repository {full_name} not found")

        repo_id = repo_obj.id

        total_commits = (
            await session.execute(
                select(func.count(CommitRecord.id)).where(CommitRecord.repo_id == repo_id)
            )
        ).scalar() or 0

        open_prs = (
            await session.execute(
                select(func.count(PullRequestRecord.id)).where(
                    PullRequestRecord.repo_id == repo_id,
                    PullRequestRecord.state == "open",
                )
            )
        ).scalar() or 0

        merged_prs = (
            await session.execute(
                select(func.count(PullRequestRecord.id)).where(
                    PullRequestRecord.repo_id == repo_id,
                    PullRequestRecord.merged_at.is_not(None),
                )
            )
        ).scalar() or 0

        closed_prs = (
            await session.execute(
                select(func.count(PullRequestRecord.id)).where(
                    PullRequestRecord.repo_id == repo_id,
                    PullRequestRecord.state == "closed",
                )
            )
        ).scalar() or 0

        open_issues = (
            await session.execute(
                select(func.count(IssueRecord.id)).where(
                    IssueRecord.repo_id == repo_id,
                    IssueRecord.state == "open",
                )
            )
        ).scalar() or 0

        closed_issues = (
            await session.execute(
                select(func.count(IssueRecord.id)).where(
                    IssueRecord.repo_id == repo_id,
                    IssueRecord.state == "closed",
                )
            )
        ).scalar() or 0

        contributors_count = (
            await session.execute(
                select(func.count(ContributorRecord.id)).where(ContributorRecord.repo_id == repo_id)
            )
        ).scalar() or 0

        lines_res = (
            await session.execute(
                select(
                    func.coalesce(func.sum(CommitRecord.lines_added), 0),
                    func.coalesce(func.sum(CommitRecord.lines_deleted), 0),
                ).where(CommitRecord.repo_id == repo_id)
            )
        ).first()

        total_lines_added = int(lines_res[0]) if lines_res else 0
        total_lines_deleted = int(lines_res[1]) if lines_res else 0
        churn = (
            round(total_lines_deleted / (total_lines_added + total_lines_deleted), 2)
            if (total_lines_added + total_lines_deleted) > 0
            else 0.0
        )

        merged_pr_rows = (
            await session.execute(
                select(PullRequestRecord.created_at, PullRequestRecord.merged_at).where(
                    PullRequestRecord.repo_id == repo_id,
                    PullRequestRecord.merged_at.is_not(None),
                )
            )
        ).all()

        cycle_diffs = [
            (m - c).total_seconds() / 3600.0
            for c, m in merged_pr_rows
            if c and m and (m - c).total_seconds() > 0
        ]
        avg_cycle = round(sum(cycle_diffs) / len(cycle_diffs), 1) if cycle_diffs else 0.0

        cp_rows = (
            (await session.execute(select(SyncCheckpoint).where(SyncCheckpoint.repo_id == repo_id)))
            .scalars()
            .all()
        )

        checkpoints = [
            SyncCheckpointItem(
                resource_type=cp.resource_type,
                status=cp.status,
                last_item_id=cp.last_item_id,
                last_checkpoint_timestamp=(
                    cp.last_checkpoint_timestamp.isoformat()
                    if cp.last_checkpoint_timestamp
                    else None
                ),
                records_synced=cp.records_synced,
            )
            for cp in cp_rows
        ]

        return RepoStatsResponse(
            repository=full_name,
            total_commits=total_commits,
            open_pull_requests=open_prs,
            merged_pull_requests=merged_prs,
            closed_pull_requests=closed_prs,
            open_issues=open_issues,
            closed_issues=closed_issues,
            total_contributors=contributors_count,
            avg_pr_cycle_time_hours=avg_cycle,
            total_lines_added=total_lines_added,
            total_lines_deleted=total_lines_deleted,
            churn_rate=churn,
            last_synced_at=repo_obj.last_synced_at.isoformat() if repo_obj.last_synced_at else None,
            monitoring_status=repo_obj.monitoring_status,
            checkpoints=checkpoints,
        )


@router.get("/repos/{owner}/{repo}/pulls", response_model=PullRequestsResponse)
async def get_repository_pull_requests(
    owner: str,
    repo: str,
    state: str | None = Query(None, pattern="^(open|closed|all)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PullRequestsResponse:
    """Retrieves paginated pull request records directly from database storage."""
    full_name = f"{owner}/{repo}"
    async with AsyncSessionLocal() as session:
        repo_obj = (
            await session.execute(select(Repository).where(Repository.full_name == full_name))
        ).scalar_one_or_none()
        if not repo_obj:
            raise HTTPException(status_code=404, detail=f"Repository {full_name} not found")

        stmt = select(PullRequestRecord).where(PullRequestRecord.repo_id == repo_obj.id)
        if state and state != "all":
            stmt = stmt.where(PullRequestRecord.state == state)

        total_count = (
            await session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar() or 0

        stmt = stmt.order_by(PullRequestRecord.created_at.desc()).offset(offset).limit(limit)
        prs = (await session.execute(stmt)).scalars().all()

        items = [
            PullRequestItem(
                id=pr.id,
                github_id=pr.github_id,
                number=pr.number,
                title=pr.title,
                state=pr.state,
                author_login=pr.author_login,
                created_at=pr.created_at.isoformat(),
                updated_at=pr.updated_at.isoformat() if pr.updated_at else None,
                closed_at=pr.closed_at.isoformat() if pr.closed_at else None,
                merged_at=pr.merged_at.isoformat() if pr.merged_at else None,
                first_reviewed_at=(
                    pr.first_reviewed_at.isoformat() if pr.first_reviewed_at else None
                ),
                additions=pr.additions,
                deletions=pr.deletions,
                changed_files=pr.changed_files,
                review_comments_count=pr.review_comments_count,
            )
            for pr in prs
        ]

        return PullRequestsResponse(
            repository=full_name,
            total_count=total_count,
            limit=limit,
            offset=offset,
            pull_requests=items,
        )


@router.get("/repos/{owner}/{repo}/issues", response_model=IssuesResponse)
async def get_repository_issues(
    owner: str,
    repo: str,
    state: str | None = Query(None, pattern="^(open|closed|all)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> IssuesResponse:
    """Retrieves paginated issue records directly from database storage."""
    full_name = f"{owner}/{repo}"
    async with AsyncSessionLocal() as session:
        repo_obj = (
            await session.execute(select(Repository).where(Repository.full_name == full_name))
        ).scalar_one_or_none()
        if not repo_obj:
            raise HTTPException(status_code=404, detail=f"Repository {full_name} not found")

        stmt = select(IssueRecord).where(IssueRecord.repo_id == repo_obj.id)
        if state and state != "all":
            stmt = stmt.where(IssueRecord.state == state)

        total_count = (
            await session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar() or 0

        stmt = stmt.order_by(IssueRecord.created_at.desc()).offset(offset).limit(limit)
        issues = (await session.execute(stmt)).scalars().all()

        items = [
            IssueItem(
                id=iss.id,
                github_id=iss.github_id,
                number=iss.number,
                title=iss.title,
                state=iss.state,
                author_login=iss.author_login,
                labels=iss.labels or [],
                comments_count=iss.comments_count,
                created_at=iss.created_at.isoformat(),
                updated_at=iss.updated_at.isoformat() if iss.updated_at else None,
                closed_at=iss.closed_at.isoformat() if iss.closed_at else None,
            )
            for iss in issues
        ]

        return IssuesResponse(
            repository=full_name,
            total_count=total_count,
            limit=limit,
            offset=offset,
            issues=items,
        )


@router.get("/repos/{owner}/{repo}/contributors", response_model=ContributorsResponse)
async def get_repository_contributors(
    owner: str,
    repo: str,
) -> ContributorsResponse:
    """Retrieves all tracked contributors for a repository with exact contribution counts."""
    full_name = f"{owner}/{repo}"
    async with AsyncSessionLocal() as session:
        repo_obj = (
            await session.execute(select(Repository).where(Repository.full_name == full_name))
        ).scalar_one_or_none()
        if not repo_obj:
            raise HTTPException(status_code=404, detail=f"Repository {full_name} not found")

        stmt = (
            select(ContributorRecord)
            .where(ContributorRecord.repo_id == repo_obj.id)
            .order_by(
                ContributorRecord.contributions_count.desc(), ContributorRecord.commits_count.desc()
            )
        )
        contribs = (await session.execute(stmt)).scalars().all()

        if not contribs:
            try:
                pipeline = DataIngestionPipeline()
                await pipeline.ingest_contributors(owner, repo, max_pages=1)
                contribs = (await session.execute(stmt)).scalars().all()
            except Exception as exc:
                logger.debug("Automatic initial contributor fetch: %s", exc)

        items = [
            ContributorItem(
                id=c.id,
                login=c.login,
                name=c.name,
                avatar_url=c.avatar_url,
                html_url=c.html_url,
                contributions_count=c.contributions_count,
                commits_count=c.commits_count,
                prs_count=c.prs_count,
                issues_count=c.issues_count,
                first_contributed_at=(
                    c.first_contributed_at.isoformat() if c.first_contributed_at else None
                ),
                last_contributed_at=(
                    c.last_contributed_at.isoformat() if c.last_contributed_at else None
                ),
            )
            for c in contribs
        ]

        return ContributorsResponse(
            repository=full_name,
            total_count=len(items),
            contributors=items,
        )


@router.post("/repos/{owner}/{repo}/sync", response_model=SyncRepositoryResponse)
async def sync_repository(
    owner: str,
    repo: str,
    incremental: bool = Query(True),
    max_pages: int = Query(2, ge=1, le=10),
) -> SyncRepositoryResponse:
    """Triggers an on-demand data pipeline synchronization run for a repository."""
    pipeline = DataIngestionPipeline()
    result = await pipeline.run_pipeline(owner, repo, incremental=incremental, max_pages=max_pages)
    return SyncRepositoryResponse(
        status=result["status"],
        pipeline_run_id=result.get("pipeline_run_id"),
        target_repo=result["target_repo"],
        records_processed=result["records_processed"],
        records_failed=result["records_failed"],
        duration_seconds=result["duration_seconds"],
        error_message=result.get("error_message"),
    )


@router.post("/repos/{owner}/{repo}/reconcile", response_model=ReconciliationResponse)
async def reconcile_repository_data(
    owner: str,
    repo: str,
) -> ReconciliationResponse:
    """Audits and heals drift between GitHub and database for commits, PRs, issues, and contributors."""
    recon_service = DataReconciliationService()
    report = await recon_service.reconcile_repository(owner, repo)
    return ReconciliationResponse(
        repository=report["repository"],
        status=report["status"],
        reconciled_at=report["reconciled_at"],
        commits=report["commits"],
        pull_requests=report["pull_requests"],
        issues=report["issues"],
        contributors=report["contributors"],
        reviews=report["reviews"],
        metrics_recalculated=report["metrics_recalculated"],
    )


@router.get("/repos/{owner}/{repo}/events", response_model=EventsResponse)
async def get_repository_events(
    owner: str,
    repo: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    event_type: str | None = None,
) -> EventsResponse:
    """Retrieves live paginated event stream for a repository."""
    full_name = f"{owner}/{repo}"

    async def _query_events():
        try:
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(GitHubEvent)
                    .join(Repository, GitHubEvent.repo_id == Repository.id)
                    .where(Repository.full_name == full_name)
                )
                if event_type:
                    stmt = stmt.where(GitHubEvent.event_type == event_type)
                stmt = stmt.order_by(GitHubEvent.created_at.desc()).offset(offset).limit(limit)
                result = await session.execute(stmt)
                return list(result.scalars().all())
        except Exception as exc:
            logger.debug("Database event lookup error for %s: %s", full_name, exc)
            return []

    records = await _query_events()

    # If no events exist in database yet, fetch live from GitHub API and persist
    if not records and offset == 0:
        client = GitHubClient()
        live_events = await client.fetch_all_recent_events(owner, repo, max_pages=3)
        if live_events:
            await _persist_events_to_db(owner, repo, live_events)
            records = await _query_events()

    db_events = [
        EventItem(
            event_id=r.event_id,
            event_type=r.event_type,
            actor=r.actor_login,
            actor_avatar_url=r.actor_avatar_url,
            action=r.action,
            payload_summary=r.payload_summary,
            created_at=(
                r.created_at.isoformat() if r.created_at else datetime.now(UTC).isoformat()
            ),
        )
        for r in records
    ]

    return EventsResponse(
        total_count=len(db_events) + offset,
        limit=limit,
        offset=offset,
        events=db_events,
    )


@router.post("/webhooks/github", status_code=status.HTTP_202_ACCEPTED)
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
) -> dict:
    """Receives, verifies, and processes GitHub webhook payloads for all contributors idempotently."""
    payload_body = await request.body()

    # 1. Verify HMAC SHA-256 signature using GITHUB_WEBHOOK_SECRET (never GITHUB_TOKEN)
    webhook_service.verify_signature(payload_body, x_hub_signature_256)

    # 2. Extract delivery ID and check idempotency to prevent duplicate notifications
    delivery_id = request.headers.get("X-GitHub-Delivery")
    if delivery_id and await webhook_service.is_delivery_processed(delivery_id):
        logger.info(
            "Webhook delivery %s already processed. Skipping duplicate delivery.", delivery_id
        )
        return {
            "status": "DUPLICATE_SKIPPED",
            "delivery_id": delivery_id,
            "bytes_received": len(payload_body),
        }

    # Fallback delivery ID for audit tracking if not provided in header
    effective_delivery_id = (
        delivery_id
        or f"del_{int(datetime.now(UTC).timestamp())}_{hashlib.sha256(payload_body).hexdigest()[:12]}"
    )

    try:
        parsed = json.loads(payload_body.decode("utf-8")) if payload_body else {}
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in webhook payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc

    event_name = request.headers.get("X-GitHub-Event", "push").lower()
    repo_dict = parsed.get("repository", {}) if isinstance(parsed.get("repository"), dict) else {}
    repo_github_id = repo_dict.get("id")
    repo_name = repo_dict.get("full_name") or "general"

    # Distinguish repository owner
    owner_info = repo_dict.get("owner", {}) if isinstance(repo_dict.get("owner"), dict) else {}
    repo_owner = (
        owner_info.get("login")
        or owner_info.get("name")
        or (repo_name.split("/")[0] if "/" in repo_name else "owner")
    )

    # Distinguish pusher, sender, and author
    pusher_dict = parsed.get("pusher", {}) if isinstance(parsed.get("pusher"), dict) else {}
    pusher_name = pusher_dict.get("name") or "developer"

    sender_dict = parsed.get("sender", {}) if isinstance(parsed.get("sender"), dict) else {}
    sender_login = sender_dict.get("login") or pusher_name
    sender_avatar = sender_dict.get("avatar_url")

    now_iso = datetime.now(UTC).isoformat()

    if event_name == "push":
        ref = parsed.get("ref") or "refs/heads/main"
        branch = ref.replace("refs/heads/", "")
        commits = parsed.get("commits") or []
        compare_url = parsed.get("compare")

        # Head commit SHA or delivery ID for immutable event identification
        head_commit_id = (
            parsed.get("after")
            or (parsed.get("head_commit") or {}).get("id")
            or (commits[-1].get("id") if commits else None)
            or f"push_{effective_delivery_id}"
        )
        push_event_id = str(head_commit_id)

        # 3. Persist incoming push event & commits to database (even if commits is empty, e.g. branch push)
        if "/" in repo_name:
            owner_p, repo_p = repo_name.split("/", 1)
        else:
            owner_p, repo_p = repo_owner, repo_name

        first_msg = (commits[0].get("message") or "").split("\n")[0][:60] if commits else ""
        suffix = f' — "{first_msg}"' if first_msg else ""
        summary_text = (
            f"New git pushed: {len(commits)} commit(s) committed to {branch} by {sender_login}{suffix}"
            if commits
            else f"New git pushed: branch {branch} updated by {sender_login}"
        )

        event_items = [
            {
                "id": push_event_id,
                "type": "PushEvent",
                "actor": {
                    "login": sender_login,
                    "avatar_url": sender_avatar,
                },
                "payload": {
                    "ref": ref,
                    "commits": commits,
                    "action": "pushed",
                    "pusher": pusher_name,
                    "sender": sender_login,
                    "compare": compare_url,
                    "repository": repo_dict,
                },
                "created_at": now_iso,
            }
        ]
        await _persist_events_to_db(owner_p, repo_p, event_items, repo_github_id=repo_github_id)

        # 4. Fetch all active repository subscribers and notify all eligible recipients
        subscribers = await subscription_service.get_subscribers_for_repo(
            repo_github_id=repo_github_id,
            full_name=repo_name,
            event_type="push",
        )
        destinations = [s["webhook_url"] for s in subscribers if s.get("webhook_url")]

        notifier = NotificationService()
        await notifier.notify_git_push(
            repo_name=repo_name,
            pusher=pusher_name,
            branch=branch,
            commits=commits,
            compare_url=compare_url,
            sender=sender_login,
            repo_owner=repo_owner,
            repo_github_id=repo_github_id,
            destinations=destinations,
        )

        # 5. Broadcast complete EventItem over WebSocket to dashboard clients
        ws_event = {
            "type": "event_stream",
            "event": {
                "event_id": push_event_id,
                "event_type": "PushEvent",
                "actor": sender_login,
                "actor_avatar_url": sender_avatar,
                "action": "pushed",
                "payload_summary": summary_text,
                "created_at": now_iso,
            },
        }
        await ws_manager.broadcast(repo_name, ws_event)
        if repo_github_id:
            await ws_manager.broadcast(str(repo_github_id), ws_event)

    elif event_name in ("repository", "create"):
        from backend.src.gitpulse.services.activity_service import activity_service

        ref_type = parsed.get("ref_type", "repository" if event_name == "repository" else "branch")
        ref_name = parsed.get("ref") or repo_name
        action = parsed.get("action", "created")

        await activity_service.record_generic_event(
            repo=repo_name,
            event_type="CreateEvent",
            actor=sender_login,
            action=action,
            summary=f"New {ref_type} {action}: {ref_name} by {sender_login}",
            raw_payload=parsed,
            repo_metadata=repo_dict,
            repo_github_id=repo_github_id,
        )

        notifier = NotificationService()
        await notifier.send_discord_notification(
            title=f"🌿 New {ref_type.capitalize()} Created: {repo_name}",
            description=f"**{sender_login}** {action} {ref_type} `{ref_name}` in **[{repo_name}](https://github.com/{repo_name})**.",
            color=0x38BDF8,
        )

    elif event_name == "pull_request":
        from backend.src.gitpulse.services.activity_service import activity_service

        pr_data = (
            parsed.get("pull_request", {}) if isinstance(parsed.get("pull_request"), dict) else {}
        )
        pr_number = pr_data.get("number") or parsed.get("number", 0)
        pr_title = pr_data.get("title", "Pull Request")
        action = parsed.get("action", "opened")

        await activity_service.record_generic_event(
            repo=repo_name,
            event_type="PullRequestEvent",
            actor=sender_login,
            action=action,
            summary=f"PR #{pr_number} {action}: {pr_title}",
            raw_payload=parsed,
            repo_metadata=repo_dict,
            repo_github_id=repo_github_id,
        )

        notifier = NotificationService()
        await notifier.notify_git_pull(
            repo_name=repo_name,
            actor=sender_login,
            action=action,
            pr_number=pr_number,
            pr_title=pr_title,
            pr_url=pr_data.get("html_url"),
        )

    elif event_name == "issues":
        from backend.src.gitpulse.services.activity_service import activity_service

        issue_data = parsed.get("issue", {}) if isinstance(parsed.get("issue"), dict) else {}
        issue_number = issue_data.get("number") or parsed.get("number", 0)
        issue_title = issue_data.get("title", "Issue")
        action = parsed.get("action", "opened")

        await activity_service.record_generic_event(
            repo=repo_name,
            event_type="IssuesEvent",
            actor=sender_login,
            action=action,
            summary=f"Issue #{issue_number} {action}: {issue_title}",
            raw_payload=parsed,
            repo_metadata=repo_dict,
            repo_github_id=repo_github_id,
        )

        notifier = NotificationService()
        await notifier.send_discord_notification(
            title=f"📌 Issue {action.upper()}: #{issue_number} in {repo_name}",
            description=f"**{sender_login}** {action} issue [#{issue_number} - {issue_title}]({issue_data.get('html_url')})",
            color=0xF59E0B,
        )

    else:
        from backend.src.gitpulse.services.activity_service import activity_service

        await activity_service.record_generic_event(
            repo=repo_name,
            event_type=f"{event_name.capitalize()}Event",
            actor=sender_login,
            action=parsed.get("action"),
            summary=f"GitHub {event_name} on {repo_name} by {sender_login}",
            raw_payload=parsed,
            repo_metadata=repo_dict,
            repo_github_id=repo_github_id,
        )

    # 6. Record processed delivery to ensure idempotency on future retries
    await webhook_service.record_delivery(
        delivery_id=effective_delivery_id,
        event_type=event_name,
        repo_github_id=repo_github_id,
        repo_full_name=repo_name,
        payload_bytes=payload_body,
        sender_login=sender_login,
    )

    return {
        "status": "ACCEPTED",
        "delivery_id": effective_delivery_id,
        "bytes_received": len(payload_body),
    }


@router.get("/repos/{owner}/{repo}/subscribers", response_model=RepoSubscribersResponse)
async def list_repo_subscribers(owner: str, repo: str) -> RepoSubscribersResponse:
    """Lists all subscribers registered for notifications on a repository."""
    full_name = f"{owner}/{repo}"
    subs = await subscription_service.list_subscribers_for_repo(full_name=full_name)
    items = [
        SubscriberItem(
            id=s["id"],
            user_id=s["user_id"],
            webhook_url=s.get("webhook_url"),
            repo_id=s.get("repo_id") or 0,
            repo_github_id=s.get("repo_github_id") or 0,
            is_active=s.get("is_active", True),
            event_types=s.get("event_types", ["push", "all"]),
        )
        for s in subs
    ]
    repo_gid = subs[0]["repo_github_id"] if subs else None
    return RepoSubscribersResponse(
        repository=full_name,
        repo_github_id=repo_gid,
        subscribers_count=len(items),
        subscribers=items,
    )


@router.post("/repos/{owner}/{repo}/subscribe", response_model=SubscribeRepoResponse)
async def subscribe_to_repo(
    owner: str,
    repo: str,
    payload: SubscribeRepoRequest,
) -> SubscribeRepoResponse:
    """Subscribes a user or channel to activity alerts for a repository."""
    full_name = f"{owner}/{repo}"
    repo_service = RepositoryService()
    tracked = await repo_service.ensure_repository_tracked(owner, repo)
    repo_github_id = tracked.get("github_id") or tracked.get("id") or 0

    sub = await subscription_service.subscribe_user(
        repo_github_id=repo_github_id,
        user_id=payload.user_id,
        repo_id=tracked.get("id"),
        webhook_url=payload.webhook_url,
        event_types=payload.event_types,
    )
    return SubscribeRepoResponse(
        status="SUBSCRIBED",
        repository=full_name,
        subscription=SubscriberItem(**sub),
    )


@router.post("/repos/{owner}/{repo}/unsubscribe", response_model=UnsubscribeRepoResponse)
async def unsubscribe_from_repo(
    owner: str,
    repo: str,
    payload: UnsubscribeRepoRequest,
) -> UnsubscribeRepoResponse:
    """Unsubscribes a user from activity alerts for a repository."""
    full_name = f"{owner}/{repo}"
    repo_service = RepositoryService()
    tracked = await repo_service.ensure_repository_tracked(owner, repo)
    repo_github_id = tracked.get("github_id") or tracked.get("id") or 0

    unsub = await subscription_service.unsubscribe_user(
        repo_github_id=repo_github_id,
        user_id=payload.user_id,
    )
    return UnsubscribeRepoResponse(
        status="UNSUBSCRIBED" if unsub else "NOT_FOUND",
        repository=full_name,
        unsubscribed=unsub,
    )


@router.post("/notify/push", response_model=UniversalPushNotificationResponse)
async def universal_push_notify(
    payload: UniversalPushNotificationRequest,
) -> UniversalPushNotificationResponse:
    """Universal notification endpoint that saves git push activity to DB and delivers alerts."""
    from backend.src.gitpulse.services.activity_service import activity_service

    commits_list = payload.commits or []
    if not commits_list and payload.message:
        commits_list = [{"id": payload.sha or "head", "message": payload.message}]

    res = await activity_service.record_commit_activity(
        repo=payload.repo,
        actor=payload.pusher,
        branch=payload.branch,
        sha=payload.sha or (commits_list[0].get("id") if commits_list else "head"),
        message=payload.message
        or (commits_list[0].get("message") if commits_list else "Push update"),
        commits=commits_list,
        compare_url=payload.compare_url,
        discord_webhook_url=payload.discord_webhook_url,
        notify_discord=True,
    )
    delivered = res.get("delivered", False)
    return UniversalPushNotificationResponse(
        status="SUCCESS",
        delivered=delivered,
        repository=res.get("repository", payload.repo),
        message="New git pushed and persisted to database",
    )


@router.post("/notify/pull", response_model=UniversalPullNotificationResponse)
async def universal_pull_notify(
    payload: UniversalPullNotificationRequest,
) -> UniversalPullNotificationResponse:
    """Universal notification endpoint that saves pull request to DB and sends Discord alerts."""
    from backend.src.gitpulse.services.activity_service import activity_service

    await activity_service.record_generic_event(
        repo=payload.repo,
        event_type="PullRequestEvent",
        actor=payload.actor,
        action=payload.action,
        summary=f"PR #{payload.pr_number} {payload.action}: {payload.pr_title or ''}",
        raw_payload={
            "action": payload.action,
            "number": payload.pr_number,
            "title": payload.pr_title,
            "html_url": payload.pr_url,
        },
    )

    notifier = NotificationService(discord_webhook_url=payload.discord_webhook_url)
    delivered = await notifier.notify_git_pull(
        repo_name=payload.repo,
        actor=payload.actor,
        action=payload.action,
        pr_number=payload.pr_number,
        pr_title=payload.pr_title,
        pr_url=payload.pr_url,
    )
    return UniversalPullNotificationResponse(
        status="SUCCESS",
        delivered=delivered,
        repository=payload.repo,
        message="New git pulled and persisted to database",
    )


@router.post("/notify/commit", response_model=UniversalCommitNotificationResponse)
async def universal_commit_notify(
    payload: UniversalCommitNotificationRequest,
) -> UniversalCommitNotificationResponse:
    """Universal notification endpoint that saves commit to DB and sends rich Discord alerts."""
    from backend.src.gitpulse.services.activity_service import activity_service

    res = await activity_service.record_commit_activity(
        repo=payload.repo,
        actor=payload.author,
        branch=payload.branch,
        sha=payload.sha,
        message=payload.message,
        commit_url=payload.commit_url,
        discord_webhook_url=payload.discord_webhook_url,
        notify_discord=True,
    )
    delivered = res.get("delivered", False)
    return UniversalCommitNotificationResponse(
        status="SUCCESS",
        delivered=delivered,
        repository=res.get("repository", payload.repo),
        message="New git committed and persisted to database",
    )


@router.post("/profile/poll")
@router.post("/profile/{username}/poll")
async def trigger_profile_poll(username: str | None = None) -> dict[str, Any]:
    """Manually triggers immediate polling of GitHub user profile activity and dispatches Discord alerts."""
    from backend.src.gitpulse.services.activity_service import resolve_effective_user
    from backend.src.gitpulse.services.profile_monitor import ProfileMonitorService

    target_user = username or settings.GITHUB_TARGET_USER or resolve_effective_user()
    monitor = ProfileMonitorService(username=target_user)
    count = await monitor.poll_and_notify()
    return {
        "status": "SUCCESS",
        "username": target_user,
        "new_alerts_dispatched": count,
        "polled_at": datetime.now(UTC).isoformat(),
    }


@router.websocket("/ws/repos/{owner}/{repo}")
async def websocket_repo_feed(websocket: WebSocket, owner: str, repo: str) -> None:
    """Real-time WebSocket stream emitting live developer events."""
    repo_key = f"{owner}/{repo}"
    await ws_manager.connect(repo_key, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
                if cmd.get("action") == "subscribe":
                    await websocket.send_json(
                        {
                            "type": "subscription_acknowledged",
                            "repository": repo_key,
                            "events": cmd.get("events", ["all"]),
                        }
                    )
            except json.JSONDecodeError:
                await websocket.send_text("Invalid JSON frame")
    except WebSocketDisconnect:
        ws_manager.disconnect(repo_key, websocket)
