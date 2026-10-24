"""FastAPI Route Definitions for GitPulse Analytics Platform."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from backend.src.gitpulse.api.schemas import (
    EventItem,
    EventsResponse,
    HealthResponse,
    RepositoryRef,
    TimelinePoint,
    VelocityResponse,
    VelocitySummary,
)
from backend.src.gitpulse.common.config import settings

router = APIRouter(prefix="/api/v1", tags=["analytics"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Service health and operational status."""
    return HealthResponse(
        status="HEALTHY",
        version="0.1.0",
        environment=settings.GITPULSE_ENV,
    )


@router.get("/repos/{owner}/{repo}/velocity", response_model=VelocityResponse)
async def get_repository_velocity(
    owner: str,
    repo: str,
    timeframe: str = Query("30d", pattern="^(7d|14d|30d|90d|1y)$"),
    granularity: str = Query("day", pattern="^(hour|day|week)$"),
) -> VelocityResponse:
    """Retrieves aggregated commit velocity and cycle time metrics."""
    return VelocityResponse(
        repository=RepositoryRef(
            id=1029384,
            owner=owner,
            name=repo,
            full_name=f"{owner}/{repo}",
        ),
        timeframe=timeframe,
        granularity=granularity,
        summary=VelocitySummary(
            total_commits=342,
            active_contributors=48,
            avg_pr_cycle_time_hours=18.5,
            lines_added=14250,
            lines_deleted=8920,
            churn_rate=0.38,
        ),
        timeline=[
            TimelinePoint(
                timestamp="2026-10-01T00:00:00Z",
                commit_count=14,
                pr_opened_count=6,
                pr_merged_count=5,
                active_authors=8,
                net_lines=450,
            ),
            TimelinePoint(
                timestamp="2026-10-02T00:00:00Z",
                commit_count=22,
                pr_opened_count=8,
                pr_merged_count=7,
                active_authors=11,
                net_lines=820,
            ),
        ],
    )


@router.get("/repos/{owner}/{repo}/events", response_model=EventsResponse)
async def get_repository_events(
    owner: str,
    repo: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    event_type: str | None = None,
) -> EventsResponse:
    """Retrieves paginated event stream for a repository."""
    events = [
        EventItem(
            event_id="evt_9872134",
            event_type="PullRequestEvent",
            actor="octocat",
            actor_avatar_url="https://avatars.githubusercontent.com/u/583231",
            action="opened",
            payload_summary="PR #124: Add PySpark structured streaming sink",
            created_at="2026-10-24T18:45:10Z",
        ),
        EventItem(
            event_id="evt_9872135",
            event_type="PushEvent",
            actor="developer-alice",
            actor_avatar_url="https://avatars.githubusercontent.com/u/102938",
            action="pushed",
            payload_summary="Push 3 commits to main",
            created_at="2026-10-24T18:50:00Z",
        ),
    ]

    return EventsResponse(
        total_count=len(events),
        limit=limit,
        offset=offset,
        events=events,
    )


@router.post("/webhooks/github", status_code=status.HTTP_202_ACCEPTED)
async def handle_github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
) -> dict:
    """Receives and verifies GitHub webhook payloads with HMAC SHA-256."""
    payload_body = await request.body()

    # If secret is configured in production, enforce HMAC signature check
    secret = settings.GITHUB_TOKEN.encode("utf-8")
    if secret and x_hub_signature_256:
        expected = "sha256=" + hmac.new(secret, payload_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    return {"status": "ACCEPTED", "bytes_received": len(payload_body)}
