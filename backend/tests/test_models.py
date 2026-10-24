"""SQLAlchemy declarative model tests."""

from datetime import datetime, timezone
from backend.src.gitpulse.storage.models import (
    CommitRecord,
    DeveloperMetric,
    GitHubEvent,
    Repository,
)


def test_repository_model_instantiation():
    repo = Repository(
        id=1,
        github_id=1234567,
        owner="apache",
        name="spark",
        full_name="apache/spark",
        stars_count=38000,
        forks_count=29000,
    )
    assert repo.full_name == "apache/spark"
    assert repo.stars_count == 38000


def test_event_and_metric_models():
    event = GitHubEvent(
        event_id="evt_001",
        event_type="PushEvent",
        repo_id=1,
        actor_login="dev-user",
        action="push",
        payload_summary="Test push event",
    )
    assert event.event_id == "evt_001"

    metric = DeveloperMetric(
        repo_id=1,
        metric_date="2026-10-24",
        commit_count=15,
        active_contributors=5,
        avg_pr_cycle_time_hours=12.5,
        churn_rate=0.22,
    )
    assert metric.commit_count == 15
    assert metric.churn_rate == 0.22
