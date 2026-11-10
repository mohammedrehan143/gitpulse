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


class KeepAliveResponse(BaseModel):
    status: str
    timestamp: str
    database: str
    repositories_count: int
    events_count: int
    last_synced_at: str | None = None
    uptime_seconds: float
    keep_alive_pulse: bool
    source: str
    message: str


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


class SubscriberItem(BaseModel):
    id: int
    user_id: str
    webhook_url: str | None = None
    repo_id: int
    repo_github_id: int
    is_active: bool
    event_types: list[str] = Field(default_factory=lambda: ["push", "all"])


class RepoSubscribersResponse(BaseModel):
    repository: str
    repo_github_id: int | None = None
    subscribers_count: int
    subscribers: list[SubscriberItem]


class SubscribeRepoRequest(BaseModel):
    user_id: str
    webhook_url: str | None = None
    event_types: list[str] = Field(default_factory=lambda: ["push", "all"])


class SubscribeRepoResponse(BaseModel):
    status: str
    repository: str
    subscription: SubscriberItem


class UnsubscribeRepoRequest(BaseModel):
    user_id: str


class UnsubscribeRepoResponse(BaseModel):
    status: str
    repository: str
    unsubscribed: bool


class SyncCheckpointItem(BaseModel):
    resource_type: str
    status: str
    last_item_id: str | None = None
    last_checkpoint_timestamp: str | None = None
    records_synced: int = 0


class RepoStatsResponse(BaseModel):
    repository: str
    total_commits: int
    open_pull_requests: int
    merged_pull_requests: int
    closed_pull_requests: int
    open_issues: int
    closed_issues: int
    total_contributors: int
    avg_pr_cycle_time_hours: float
    total_lines_added: int
    total_lines_deleted: int
    churn_rate: float
    last_synced_at: str | None = None
    monitoring_status: str
    checkpoints: list[SyncCheckpointItem] = Field(default_factory=list)


class PullRequestItem(BaseModel):
    id: int
    github_id: int
    number: int
    title: str
    state: str
    author_login: str
    created_at: str
    updated_at: str | None = None
    closed_at: str | None = None
    merged_at: str | None = None
    first_reviewed_at: str | None = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    review_comments_count: int = 0


class PullRequestsResponse(BaseModel):
    repository: str
    total_count: int
    limit: int
    offset: int
    pull_requests: list[PullRequestItem]


class IssueItem(BaseModel):
    id: int
    github_id: int
    number: int
    title: str
    state: str
    author_login: str
    labels: list[str] = Field(default_factory=list)
    comments_count: int = 0
    created_at: str
    updated_at: str | None = None
    closed_at: str | None = None


class IssuesResponse(BaseModel):
    repository: str
    total_count: int
    limit: int
    offset: int
    issues: list[IssueItem]


class ContributorItem(BaseModel):
    id: int
    login: str
    name: str | None = None
    avatar_url: str | None = None
    html_url: str | None = None
    contributions_count: int = 0
    commits_count: int = 0
    prs_count: int = 0
    issues_count: int = 0
    first_contributed_at: str | None = None
    last_contributed_at: str | None = None


class ContributorsResponse(BaseModel):
    repository: str
    total_count: int
    contributors: list[ContributorItem]


class SyncRepositoryResponse(BaseModel):
    status: str
    pipeline_run_id: int | None = None
    target_repo: str
    records_processed: int
    records_failed: int
    duration_seconds: float
    error_message: str | None = None


class ReconciliationResponse(BaseModel):
    repository: str
    status: str
    reconciled_at: str
    commits: dict[str, Any]
    pull_requests: dict[str, Any]
    issues: dict[str, Any]
    contributors: dict[str, Any]
    reviews: dict[str, Any]
    metrics_recalculated: bool
