"""Pydantic Request & Response Schemas for GitPulse API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RepositoryRef(BaseModel):
    id: int
    owner: str
    name: str
    full_name: str


class VelocitySummary(BaseModel):
    total_commits: int
    active_contributors: int
    avg_pr_cycle_time_hours: float
    lines_added: int = Field(default=0)
    lines_deleted: int = Field(default=0)
    churn_rate: float = Field(default=0.0)


class TimelinePoint(BaseModel):
    timestamp: str
    commit_count: int
    pr_opened_count: int
    pr_merged_count: int
    active_authors: int
    net_lines: int


class VelocityResponse(BaseModel):
    repository: RepositoryRef
    timeframe: str
    granularity: str
    summary: VelocitySummary
    timeline: list[TimelinePoint]


class EventItem(BaseModel):
    event_id: str
    event_type: str
    actor: str
    actor_avatar_url: str | None = None
    action: str | None = None
    payload_summary: str | None = None
    created_at: str


class EventsResponse(BaseModel):
    total_count: int
    limit: int
    offset: int
    events: list[EventItem]


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class DiscoveredRepositoryItem(BaseModel):
    id: int
    github_id: int | None = None
    owner: str
    name: str
    full_name: str
    description: str | None = None
    visibility: str = "public"
    default_branch: str = "main"
    html_url: str | None = None
    pushed_at: str | None = None
    created_at: str | None = None
    is_active: bool = True
    monitoring_status: str = "DISCOVERED"
    last_synced_at: str | None = None
    stars_count: int = 0
    forks_count: int = 0


class RepositoriesResponse(BaseModel):
    total_count: int
    auto_discover_enabled: bool
    repositories: list[DiscoveredRepositoryItem]


class RefreshRepositoriesResponse(BaseModel):
    status: str
    synced_count: int
    repositories: list[DiscoveredRepositoryItem]


class AIGenerateRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None
    model: str | None = None


class AIGenerateResponse(BaseModel):
    model: str
    response: str


class AIInsightsResponse(BaseModel):
    repository: str
    model: str
    insights: str


class UniversalPushNotificationRequest(BaseModel):
    repo: str
    pusher: str = "developer"
    branch: str = "main"
    message: str | None = None
    sha: str | None = None
    commits: list[dict[str, Any]] | None = None
    compare_url: str | None = None
    discord_webhook_url: str | None = None


class UniversalPushNotificationResponse(BaseModel):
    status: str
    delivered: bool
    repository: str
    message: str = "New git pushed"


class UniversalPullNotificationRequest(BaseModel):
    repo: str
    actor: str = "developer"
    action: str = "merged"
    pr_number: int | str = 1
    pr_title: str = "Pull Request"
    pr_url: str | None = None
    discord_webhook_url: str | None = None


class UniversalPullNotificationResponse(BaseModel):
    status: str
    delivered: bool
    repository: str
    message: str = "New git pulled"


class UniversalCommitNotificationRequest(BaseModel):
    repo: str
    author: str = "developer"
    message: str = "Committed changes"
    sha: str = "head"
    branch: str = "main"
    commit_url: str | None = None
    discord_webhook_url: str | None = None


class UniversalCommitNotificationResponse(BaseModel):
    status: str
    delivered: bool
    repository: str
    message: str = "New git committed"
