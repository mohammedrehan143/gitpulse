"""Pydantic Request & Response Schemas for GitPulse API."""

from __future__ import annotations

from typing import List, Optional
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
    timeline: List[TimelinePoint]


class EventItem(BaseModel):
    event_id: str
    event_type: str
    actor: str
    actor_avatar_url: Optional[str] = None
    action: Optional[str] = None
    payload_summary: Optional[str] = None
    created_at: str


class EventsResponse(BaseModel):
    total_count: int
    limit: int
    offset: int
    events: List[EventItem]


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
