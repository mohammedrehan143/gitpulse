"""Declarative SQLAlchemy 2.0 Models for GitPulse Storage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.src.gitpulse.storage.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    owner: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    full_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    stars_count: Mapped[int] = mapped_column(Integer, default=0)
    forks_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    events: Mapped[list["GitHubEvent"]] = relationship("GitHubEvent", back_populates="repository")
    metrics: Mapped[list["DeveloperMetric"]] = relationship("DeveloperMetric", back_populates="repository")


class GitHubEvent(Base):
    __tablename__ = "github_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    repo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repositories.id"), index=True)
    actor_login: Mapped[str] = mapped_column(String(100), index=True)
    actor_avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payload_summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    repository: Mapped["Repository"] = relationship("Repository", back_populates="events")


class CommitRecord(Base):
    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
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

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repositories.id"), index=True)
    metric_date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    commit_count: Mapped[int] = mapped_column(Integer, default=0)
    active_contributors: Mapped[int] = mapped_column(Integer, default=0)
    avg_pr_cycle_time_hours: Mapped[float] = mapped_column(Float, default=0.0)
    lines_added: Mapped[int] = mapped_column(Integer, default=0)
    lines_deleted: Mapped[int] = mapped_column(Integer, default=0)
    churn_rate: Mapped[float] = mapped_column(Float, default=0.0)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="metrics")
