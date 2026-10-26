"""Declarative SQLAlchemy 2.0 Models for GitPulse Storage."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.gitpulse.storage.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    owner: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    full_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="public")
    default_branch: Mapped[str] = mapped_column(String(50), default="main")
    html_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    monitoring_status: Mapped[str] = mapped_column(String(30), default="DISCOVERED")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stars_count: Mapped[int] = mapped_column(Integer, default=0)
    forks_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    events: Mapped[list[GitHubEvent]] = relationship("GitHubEvent", back_populates="repository")
    metrics: Mapped[list[DeveloperMetric]] = relationship(
        "DeveloperMetric", back_populates="repository"
    )
    pull_requests: Mapped[list[PullRequestRecord]] = relationship(
        "PullRequestRecord", back_populates="repository"
    )
    issues: Mapped[list[IssueRecord]] = relationship("IssueRecord", back_populates="repository")


class GitHubEvent(Base):
    __tablename__ = "github_events"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    repo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repositories.id"), index=True)
    actor_login: Mapped[str] = mapped_column(String(100), index=True)
    actor_avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payload_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    repository: Mapped[Repository] = relationship("Repository", back_populates="events")


class CommitRecord(Base):
    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    sha: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    repo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repositories.id"), index=True)
    author_name: Mapped[str] = mapped_column(String(100))
    author_email: Mapped[str] = mapped_column(String(150))
    message: Mapped[str] = mapped_column(String(1000))
    lines_added: Mapped[int] = mapped_column(Integer, default=0)
    lines_deleted: Mapped[int] = mapped_column(Integer, default=0)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DeveloperMetric(Base):
    __tablename__ = "developer_metrics"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    repo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repositories.id"), index=True)
    metric_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    commit_count: Mapped[int] = mapped_column(Integer, default=0)
    active_contributors: Mapped[int] = mapped_column(Integer, default=0)
    avg_pr_cycle_time_hours: Mapped[float] = mapped_column(Float, default=0.0)
    lines_added: Mapped[int] = mapped_column(Integer, default=0)
    lines_deleted: Mapped[int] = mapped_column(Integer, default=0)
    churn_rate: Mapped[float] = mapped_column(Float, default=0.0)

    repository: Mapped[Repository] = relationship("Repository", back_populates="metrics")


class PullRequestRecord(Base):
    __tablename__ = "pull_requests"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    repo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repositories.id"), index=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="open", index=True)
    author_login: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    changed_files: Mapped[int] = mapped_column(Integer, default=0)
    review_comments_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    repository: Mapped[Repository] = relationship("Repository", back_populates="pull_requests")
    reviews: Mapped[list[ReviewRecord]] = relationship(
        "ReviewRecord", back_populates="pull_request"
    )


class ReviewRecord(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    pr_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pull_requests.id"), index=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    reviewer_login: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(50))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    body: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    pull_request: Mapped[PullRequestRecord] = relationship(
        "PullRequestRecord", back_populates="reviews"
    )


class IssueRecord(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    repo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repositories.id"), index=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    number: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="open", index=True)
    author_login: Mapped[str] = mapped_column(String(100), index=True)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    reopened_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    repository: Mapped[Repository] = relationship("Repository", back_populates="issues")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    pipeline_name: Mapped[str] = mapped_column(String(100), index=True)
    target_repo: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True, default="RUNNING")
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
