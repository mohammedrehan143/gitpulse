"""API unit tests for GitPulse FastAPI endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

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
        assert data["summary"]["total_commits"] == 342
        assert len(data["timeline"]) >= 1


@pytest.mark.asyncio
async def test_get_repository_events():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/repos/apache/spark/events?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert len(data["events"]) >= 1
