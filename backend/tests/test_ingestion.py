"""Ingestion and Kafka streaming tests."""

import pytest

from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.ingestion.kafka_producer import KafkaEventProducer
from backend.src.gitpulse.services.analytics import AnalyticsService


@pytest.mark.asyncio
async def test_synthetic_github_events():
    client = GitHubClient(token="")
    events = await client.fetch_synthetic_events("apache", "spark")
    assert len(events) == 2
    assert events[0]["type"] == "PushEvent"
    assert events[1]["type"] == "PullRequestEvent"


def test_kafka_event_producer_buffering():
    producer = KafkaEventProducer(topic="test.topic")
    success = producer.publish_event("apache/spark", {"event": "commit", "count": 1})
    assert success is True

    buffered = producer.get_buffered_events()
    assert len(buffered) == 1
    assert buffered[0]["key"] == "apache/spark"


def test_analytics_metrics_calculation():
    synthetic_events = [
        {"type": "PushEvent", "actor": {"login": "alice"}, "payload": {"commits": [1, 2]}},
        {"type": "PushEvent", "actor": {"login": "bob"}, "payload": {"commits": [1]}},
        {
            "type": "PullRequestEvent",
            "actor": {"login": "charlie"},
            "payload": {"action": "opened"},
        },
    ]
    summary = AnalyticsService.calculate_metrics_summary(synthetic_events)
    assert summary["total_commits"] == 3
    assert summary["active_contributors"] == 3
    assert summary["prs_opened"] == 1
