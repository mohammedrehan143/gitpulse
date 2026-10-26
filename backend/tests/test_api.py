"""API unit tests for GitPulse FastAPI endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from backend.src.gitpulse.api.main import app


@pytest.mark.asyncio
async def test_root_status_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["service"] == "GitPulse Analytics API"

        # Also test system health endpoint
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_cors_headers_for_vercel_and_render():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Vercel deployment preview/production origin
        res_vercel = await client.get(
            "/api/v1/health",
            headers={"Origin": "https://gitpulse-frontend.vercel.app"},
        )
        assert res_vercel.status_code == 200
        assert (
            res_vercel.headers.get("access-control-allow-origin")
            == "https://gitpulse-frontend.vercel.app"
        )

        # Render deployment origin
        res_render = await client.get(
            "/api/v1/health",
            headers={"Origin": "https://gitpulse-dashboard.onrender.com"},
        )
        assert res_render.status_code == 200
        assert (
            res_render.headers.get("access-control-allow-origin")
            == "https://gitpulse-dashboard.onrender.com"
        )


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


@pytest.mark.asyncio
async def test_list_discovered_repositories():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/repos")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "auto_discover_enabled" in data
        assert isinstance(data["repositories"], list)
        if data["repositories"]:
            repo = data["repositories"][0]
            assert "full_name" in repo
            assert "visibility" in repo
            assert "monitoring_status" in repo


@pytest.mark.asyncio
async def test_refresh_discovered_repositories():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/repos/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SYNCHRONIZED"
        assert "synced_count" in data
        assert isinstance(data["repositories"], list)


@pytest.mark.asyncio
async def test_ai_generate_endpoint(monkeypatch):
    from backend.src.gitpulse.services.ai_service import GroqAIService

    monkeypatch.setattr(
        GroqAIService,
        "generate_completion",
        lambda self, prompt, system_prompt=None: "Mocked Groq Response",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ai/generate",
            json={"prompt": "Explain commit velocity", "model": "openai/gpt-oss-120b"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "openai/gpt-oss-120b"
        assert data["response"] == "Mocked Groq Response"


@pytest.mark.asyncio
async def test_ai_insights_endpoint(monkeypatch):
    from backend.src.gitpulse.services.ai_service import GroqAIService

    monkeypatch.setattr(
        GroqAIService,
        "analyze_repository_metrics",
        lambda self, repo_full_name, metrics: f"Insights for {repo_full_name}: Velocity high",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/repos/apache/spark/ai-insights")
        assert resp.status_code == 200
        data = resp.json()
        assert data["repository"] == "apache/spark"
        assert "Velocity high" in data["insights"]
