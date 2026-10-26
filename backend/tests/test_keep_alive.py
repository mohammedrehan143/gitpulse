"""Tests for GitPulse Autonomous Keep-Alive & Self-Warming Pulse Engine."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.gitpulse.api.main import app
from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.services.keep_alive_service import KeepAliveService


@pytest.mark.asyncio
async def test_keep_alive_endpoint_get():
    """Verify that GET /api/v1/keepalive returns a valid keep-alive pulse payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/keepalive?source=test_suite")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ALIVE"
        assert data["keep_alive_pulse"] is True
        assert data["source"] == "test_suite"
        assert "database" in data
        assert isinstance(data["repositories_count"], int)
        assert isinstance(data["events_count"], int)
        assert isinstance(data["uptime_seconds"], (int, float))
        assert "kept awake successfully" in data["message"]


@pytest.mark.asyncio
async def test_top_level_keepalive_endpoint():
    """Verify that GET /keepalive at the root level functions identically."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/keepalive?source=root_pinger")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ALIVE"
        assert data["source"] == "root_pinger"


@pytest.mark.asyncio
async def test_keep_alive_post_endpoint():
    """Verify POST /api/v1/keepalive works for webhook or external trigger compatibility."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/keepalive?source=cron_webhook")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ALIVE"
        assert data["source"] == "cron_webhook"


def test_keep_alive_service_resolve_url(monkeypatch):
    """Verify resolution of Render and external backend URLs."""
    service = KeepAliveService()

    # When no URL is set
    monkeypatch.setattr(settings, "RENDER_EXTERNAL_URL", "")
    monkeypatch.setattr(settings, "BACKEND_PUBLIC_URL", "")
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.delenv("BACKEND_URL", raising=False)
    assert service.resolve_target_url() is None

    # When RENDER_EXTERNAL_URL is set in settings
    monkeypatch.setattr(settings, "RENDER_EXTERNAL_URL", "https://gitpulse-backend.onrender.com")
    assert service.resolve_target_url() == "https://gitpulse-backend.onrender.com"

    # When URL lacks scheme prefix
    monkeypatch.setattr(settings, "RENDER_EXTERNAL_URL", "gitpulse-backend.onrender.com/")
    assert service.resolve_target_url() == "https://gitpulse-backend.onrender.com"


@pytest.mark.asyncio
async def test_keep_alive_service_lifecycle():
    """Verify service start and stop mechanisms."""
    import asyncio

    service = KeepAliveService()
    task = service.start()
    assert task is not None
    assert service._running is True

    # Stopping service and waiting for loop to finish cancellation
    service.stop()
    assert service._running is False
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert task.done()
