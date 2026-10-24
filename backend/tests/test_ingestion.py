"""Ingestion and Kafka streaming tests."""

from __future__ import annotations

import pytest

from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.ingestion.kafka_producer import KafkaEventProducer
from backend.src.gitpulse.ingestion.runner import ingest_repository_events
from backend.src.gitpulse.services.analytics import AnalyticsService
from backend.src.gitpulse.services.processor import StreamProcessor
from data_platform.spark.batch_aggregator import SparkBatchAggregator
from data_platform.storage.iceberg_catalog import IcebergCatalogConfig
from data_platform.storage.minio_client import LakehouseStorageClient


@pytest.mark.asyncio
async def test_synthetic_github_events():
    client = GitHubClient(token="")
    events = await client.fetch_synthetic_events("apache", "spark")
    assert len(events) == 2
    assert events[0]["type"] == "PushEvent"
    assert events[1]["type"] == "PullRequestEvent"


@pytest.mark.asyncio
async def test_github_client_rate_limit_tracking():
    client = GitHubClient(token="", rate_limit_buffer=50)
    client.rate_limit_remaining = 30
    client.rate_limit_reset = 1792860000
    client.rate_limit_total = 60

    status = client.get_rate_limit_status()
    assert status["is_exhausted"] is True
    assert status["remaining"] == 30

    # With exhausted budget, fetching repository events safely yields synthetic fallback
    events = await client.fetch_repository_events("apache", "spark")
    assert len(events) == 2


@pytest.mark.asyncio
async def test_github_client_webhook_signature_verification():
    secret = "gitpulse_secret_key"
    payload = b'{"action":"opened","repository":{"full_name":"apache/spark"}}'

    import hashlib
    import hmac

    valid_signature = (
        "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    )
    assert GitHubClient.verify_webhook_signature(payload, valid_signature, secret) is True
    assert GitHubClient.verify_webhook_signature(payload, "sha256=invalid", secret) is False
    assert GitHubClient.verify_webhook_signature(payload, None, secret) is False


def test_kafka_event_producer_buffering_and_routing():
    producer = KafkaEventProducer()

    # Route PushEvent -> commits topic
    push_evt = {
        "event_id": "evt_push_1",
        "event_type": "PushEvent",
        "repo_id": 101,
        "actor_login": "dev-alice",
        "created_at": "2026-10-24T20:00:00Z",
    }
    assert producer.publish_event("apache/spark", push_evt, validate=True) is True

    # Route PullRequestEvent -> PRs topic
    pr_evt = {
        "event_id": "evt_pr_1",
        "event_type": "PullRequestEvent",
        "repo_id": 101,
        "actor_login": "dev-bob",
        "created_at": "2026-10-24T20:05:00Z",
    }
    assert producer.publish_event("apache/spark", pr_evt, validate=True) is True

    buffered = producer.get_buffered_events()
    assert len(buffered) == 2
    assert "commits" in buffered[0]["topic"]
    assert "pull_requests" in buffered[1]["topic"]

    producer.clear_buffer()
    assert len(producer.get_buffered_events()) == 0


def test_kafka_event_producer_schema_validation_failure():
    producer = KafkaEventProducer()
    # Missing actor_login and created_at
    invalid_event = {"event_id": "evt_invalid", "event_type": "PushEvent"}
    is_valid, err = producer.validate_event_schema(invalid_event)
    assert is_valid is False
    assert "Missing required fields" in (err or "")
    # publish_event with validate=True should reject
    assert producer.publish_event("apache/spark", invalid_event, validate=True) is False


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


def test_spark_batch_aggregator_velocity_and_churn():
    aggregator = SparkBatchAggregator()
    raw_events = [
        {
            "event_id": "e1",
            "event_type": "PushEvent",
            "repo_name": "apache/spark",
            "actor_login": "alice",
            "payload": {"commits": [1, 2], "added_lines": 50, "deleted_lines": 10},
        },
        {
            # Duplicate event_id should be safely deduplicated
            "event_id": "e1",
            "event_type": "PushEvent",
            "repo_name": "apache/spark",
            "actor_login": "alice",
            "payload": {"commits": [1, 2]},
        },
        {
            "event_id": "e2",
            "event_type": "PullRequestEvent",
            "repo_name": "apache/spark",
            "actor_login": "bob",
            "payload": {"action": "closed", "cycle_time_hours": 12.0},
        },
    ]

    results = aggregator.compute_daily_velocity(raw_events)
    assert len(results) == 1
    res = results[0]
    assert res["repo_name"] == "apache/spark"
    assert res["total_commits"] == 2
    assert res["total_prs_merged"] == 1
    assert res["active_contributors_count"] == 2
    assert res["lines_added"] == 50
    assert res["lines_deleted"] == 10
    assert res["churn_rate"] == 0.17
    assert res["avg_pr_cycle_time_hours"] == 12.0


def test_stream_processor_watermarking():
    processor = StreamProcessor()
    evts = [
        {"id": "evt_100", "type": "PushEvent", "actor": {"login": "charlie"}},
        {"id": "evt_100", "type": "PushEvent", "actor": {"login": "charlie"}},
        {"id": "evt_101", "type": "PullRequestEvent", "actor": {"login": "david"}},
    ]

    unique = processor.deduplicate_events(evts)
    assert len(unique) == 2
    stats = processor.get_watermark_stats()
    assert stats["unique_tracked_events"] == 2


def test_storage_connectors():
    # Test Iceberg Catalog configuration
    props = IcebergCatalogConfig.get_catalog_properties()
    assert props["type"] == "rest"
    assert "warehouse" in props

    table_defs = IcebergCatalogConfig.get_lakehouse_table_definitions()
    assert len(table_defs) >= 2

    # Test MinIO storage client
    client = LakehouseStorageClient(endpoint="localhost:9000", bucket="gitpulse-lakehouse")
    part_path = client.build_partition_path("apache/spark", "2026-10-24")
    assert "repo=apache_spark" in part_path
    assert "year=2026/month=10/day=24" in part_path

    upload_receipt = client.upload_parquet_table("raw_events", part_path, data=None)
    assert upload_receipt["status"] == "UPLOADED"
    assert "apache_spark" in upload_receipt["key"]


@pytest.mark.asyncio
async def test_ingest_repository_events_runner(monkeypatch):
    # Test runner execution with synthetic/mock data
    async def mock_fetch_all(self, owner, repo, max_pages=3, per_page=30):
        return await self.fetch_synthetic_events(owner, repo)

    monkeypatch.setattr(GitHubClient, "fetch_all_recent_events", mock_fetch_all)

    res = await ingest_repository_events(
        repos=["test-owner/test-repo", "invalid_repo"], max_pages=1
    )
    assert "test-owner/test-repo" in res
    assert res["test-owner/test-repo"] >= 2
    assert "invalid_repo" not in res
