"""Integration Tests for GitPulse Intelligence API Endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.gitpulse.api.main import app
from backend.src.gitpulse.storage.database import init_db


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


@pytest.mark.asyncio
async def test_api_forecasting():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/intelligence/test-owner/test-repo/forecasting?horizon=7")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("SUCCESS", "INSUFFICIENT_HISTORY")
        if data["status"] == "SUCCESS":
            assert len(data["forecast"]) == 7
            assert "lower_bound" in data["forecast"][0]
            assert "upper_bound" in data["forecast"][0]


@pytest.mark.asyncio
async def test_api_anomalies():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/intelligence/test-owner/test-repo/anomalies?threshold=3.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ANALYZED"
        assert "anomalies" in data
        assert data["threshold_used"] == 3.0


@pytest.mark.asyncio
async def test_api_issue_resolution_and_predict():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Insights
        insights_resp = await client.get(
            "/api/v1/intelligence/test-owner/test-repo/issue-resolution"
        )
        assert insights_resp.status_code == 200
        insights_data = insights_resp.json()
        assert insights_data["status"] in ("TRAINED", "INSUFFICIENT_DATA")

        # Predict valid
        pred_resp = await client.post(
            "/api/v1/intelligence/test-owner/test-repo/issue-resolution/predict",
            json={
                "title": "Fix database connection leak in session pool",
                "body": "When concurrency exceeds 50, connections timeout",
                "labels": ["bug", "backend"],
            },
        )
        assert pred_resp.status_code == 200
        pred_data = pred_resp.json()
        assert pred_data["predicted_duration_hours"] > 0
        assert "confidence_tier" in pred_data

        # Predict invalid (title too short)
        invalid_resp = await client.post(
            "/api/v1/intelligence/test-owner/test-repo/issue-resolution/predict",
            json={"title": "ab"},
        )
        assert invalid_resp.status_code == 422


@pytest.mark.asyncio
async def test_api_pr_review_delay_and_predict():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Insights
        insights_resp = await client.get(
            "/api/v1/intelligence/test-owner/test-repo/pr-review-delay"
        )
        assert insights_resp.status_code == 200
        insights_data = insights_resp.json()
        assert "statistics" in insights_data

        # Predict valid
        pred_resp = await client.post(
            "/api/v1/intelligence/test-owner/test-repo/pr-review-delay/predict",
            json={
                "title": "feat: Add high-throughput streaming Kafka connector",
                "additions": 450,
                "deletions": 50,
                "changed_files": 8,
            },
        )
        assert pred_resp.status_code == 200
        pred_data = pred_resp.json()
        assert pred_data["predicted_delay_hours"] > 0

        # Predict invalid (negative additions)
        invalid_resp = await client.post(
            "/api/v1/intelligence/test-owner/test-repo/pr-review-delay/predict",
            json={"title": "test pr", "additions": -10},
        )
        assert invalid_resp.status_code == 422


@pytest.mark.asyncio
async def test_api_train_all():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/intelligence/test-owner/test-repo/train")
        assert resp.status_code == 200
        data = resp.json()
        assert "issue_resolution_model" in data
        assert "pr_review_delay_model" in data
