"""API unit tests for GitPulse FastAPI endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from backend.src.gitpulse.api.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "HEALTHY"
        assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_get_repository_velocity():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/repos/apache/spark/velocity?timeframe=30d&granularity=day"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["repository"]["full_name"] == "apache/spark"
        assert data["summary"]["total_commits"] > 0
        assert data["summary"]["churn_rate"] >= 0.0
        assert len(data["timeline"]) == 30


@pytest.mark.asyncio
async def test_get_repository_events_with_filter():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/repos/apache/spark/events?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 2
        assert len(data["events"]) == 2

        # Test filtering by event_type
        filter_resp = await client.get(
            "/api/v1/repos/apache/spark/events?event_type=PullRequestEvent"
        )
        assert filter_resp.status_code == 200
        filter_data = filter_resp.json()
        for evt in filter_data["events"]:
            assert evt["event_type"] == "PullRequestEvent"


@pytest.mark.asyncio
async def test_webhook_ingestion_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ingestion accepts valid JSON payload
        resp = await client.post(
            "/api/v1/webhooks/github",
            json={"repository": {"full_name": "apache/spark"}, "sender": {"login": "octocat"}},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "ACCEPTED"


def test_websocket_repo_feed_subscription():
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/repos/apache/spark") as websocket:
        websocket.send_json({"action": "subscribe", "events": ["metrics_update", "new_event"]})
        data = websocket.receive_json()
        assert data["type"] == "subscription_acknowledged"
        assert data["repository"] == "apache/spark"
        assert "metrics_update" in data["events"]
