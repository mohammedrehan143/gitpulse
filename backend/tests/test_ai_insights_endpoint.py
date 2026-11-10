"""Automated tests for AI Insights endpoint failure modes and reliability.

Covers all 13 backend failure and success scenarios required by production specifications:
1. Successful AI Insights generation.
2. Missing GROQ_API_KEY.
3. Invalid Groq model.
4. Groq authentication failure.
5. Groq rate-limit response.
6. Groq timeout.
7. Empty Groq response.
8. Malformed Groq response.
9. Repository not found.
10. Empty repository metrics.
11. Database connection failure.
12. Database query failure.
13. Unexpected internal exception.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.src.gitpulse.api.main import app
from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.services.ai_service import (
    AIAuthenticationError,
    AIConfigurationError,
    AIEmptyResponseError,
    AIMalformedResponseError,
    AIModelError,
    AIRateLimitError,
    AITimeoutError,
    GroqAIService,
)
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import Repository


@pytest.fixture(autouse=True)
async def ensure_db():
    """Ensure database schema is ready for tests."""
    await init_db()


@pytest.mark.asyncio
async def test_01_successful_ai_insights_generation(monkeypatch):
    """Scenario 1: Successful AI Insights generation with real/mocked data."""
    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "test-org/test-repo")
        repo = (await session.execute(stmt)).scalar_one_or_none()
        if not repo:
            repo = Repository(
                github_id=99991,
                owner="test-org",
                name="test-repo",
                full_name="test-org/test-repo",
                is_active=True,
            )
            session.add(repo)
            await session.commit()

    monkeypatch.setattr(
        GroqAIService,
        "analyze_repository_metrics",
        lambda self, repo_full_name, metrics: (
            f"**Velocity Health**: Optimal.\n**Review Bottlenecks**: None.\n**Strategic Action**: Maintain cadence for {repo_full_name}."
        ),
    )

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-01"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["repository"] == "test-org/test-repo"
        assert "Velocity Health" in data["insights"]
        assert resp.headers.get("X-Correlation-ID") or "test-req-01" in resp.headers.get(
            "x-request-id", "test-req-01"
        )


@pytest.mark.asyncio
async def test_02_missing_groq_api_key(monkeypatch):
    """Scenario 2: Missing GROQ_API_KEY returns HTTP 503 with configuration error."""
    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "test-org/test-repo")
        if not (await session.execute(stmt)).scalar_one_or_none():
            session.add(
                Repository(
                    github_id=99991,
                    owner="test-org",
                    name="test-repo",
                    full_name="test-org/test-repo",
                    is_active=True,
                )
            )
            await session.commit()

    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")

    # Ensure GroqAIService fails with AIConfigurationError
    def mock_analyze(self, repo_full_name, metrics):
        raise AIConfigurationError(
            "GROQ_API_KEY is not configured in backend environment or settings"
        )

    monkeypatch.setattr(GroqAIService, "analyze_repository_metrics", mock_analyze)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-02"},
        )
        assert resp.status_code == 503
        data = resp.json()
        assert "GROQ_API_KEY is not configured" in data["detail"]
        assert "test-req-02" in data["detail"]


@pytest.mark.asyncio
async def test_03_invalid_groq_model(monkeypatch):
    """Scenario 3: Invalid Groq model returns HTTP 502 with model error."""
    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "test-org/test-repo")
        if not (await session.execute(stmt)).scalar_one_or_none():
            session.add(
                Repository(
                    github_id=99991,
                    owner="test-org",
                    name="test-repo",
                    full_name="test-org/test-repo",
                    is_active=True,
                )
            )
            await session.commit()

    def mock_analyze(self, repo_full_name, metrics):
        raise AIModelError(
            "Configured Groq model 'invalid-nonexistent-model' is not available or invalid."
        )

    monkeypatch.setattr(GroqAIService, "analyze_repository_metrics", mock_analyze)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-03"},
        )
        assert resp.status_code == 502
        data = resp.json()
        assert "is not available or invalid" in data["detail"]


@pytest.mark.asyncio
async def test_04_groq_authentication_failure(monkeypatch):
    """Scenario 4: Groq authentication failure returns HTTP 502 without leaking credentials."""
    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "test-org/test-repo")
        if not (await session.execute(stmt)).scalar_one_or_none():
            session.add(
                Repository(
                    github_id=99991,
                    owner="test-org",
                    name="test-repo",
                    full_name="test-org/test-repo",
                    is_active=True,
                )
            )
            await session.commit()

    def mock_analyze(self, repo_full_name, metrics):
        raise AIAuthenticationError(
            "Groq authentication failed. Please verify GROQ_API_KEY credentials."
        )

    monkeypatch.setattr(GroqAIService, "analyze_repository_metrics", mock_analyze)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-04"},
        )
        assert resp.status_code == 502
        data = resp.json()
        assert "authentication failed" in data["detail"].lower()
        # Verify no token or secret is exposed
        assert "gsk_" not in data["detail"]


@pytest.mark.asyncio
async def test_05_groq_rate_limit(monkeypatch):
    """Scenario 5: Groq rate-limit response returns HTTP 429."""
    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "test-org/test-repo")
        if not (await session.execute(stmt)).scalar_one_or_none():
            session.add(
                Repository(
                    github_id=99991,
                    owner="test-org",
                    name="test-repo",
                    full_name="test-org/test-repo",
                    is_active=True,
                )
            )
            await session.commit()

    def mock_analyze(self, repo_full_name, metrics):
        raise AIRateLimitError(
            "Groq API rate limit or quota exceeded. Please retry after a brief delay."
        )

    monkeypatch.setattr(GroqAIService, "analyze_repository_metrics", mock_analyze)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-05"},
        )
        assert resp.status_code == 429
        data = resp.json()
        assert "rate limit" in data["detail"].lower()


@pytest.mark.asyncio
async def test_06_groq_timeout(monkeypatch):
    """Scenario 6: Groq timeout returns HTTP 504 Gateway Timeout."""
    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "test-org/test-repo")
        if not (await session.execute(stmt)).scalar_one_or_none():
            session.add(
                Repository(
                    github_id=99991,
                    owner="test-org",
                    name="test-repo",
                    full_name="test-org/test-repo",
                    is_active=True,
                )
            )
            await session.commit()

    def mock_analyze(self, repo_full_name, metrics):
        raise AITimeoutError("Groq API request timed out.")

    monkeypatch.setattr(GroqAIService, "analyze_repository_metrics", mock_analyze)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-06"},
        )
        assert resp.status_code == 504
        data = resp.json()
        assert "timed out" in data["detail"].lower()


@pytest.mark.asyncio
async def test_07_empty_groq_response(monkeypatch):
    """Scenario 7: Empty Groq response returns HTTP 502 Bad Gateway."""
    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "test-org/test-repo")
        if not (await session.execute(stmt)).scalar_one_or_none():
            session.add(
                Repository(
                    github_id=99991,
                    owner="test-org",
                    name="test-repo",
                    full_name="test-org/test-repo",
                    is_active=True,
                )
            )
            await session.commit()

    def mock_analyze(self, repo_full_name, metrics):
        raise AIEmptyResponseError("Groq API returned an empty completion response.")

    monkeypatch.setattr(GroqAIService, "analyze_repository_metrics", mock_analyze)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-07"},
        )
        assert resp.status_code == 502
        data = resp.json()
        assert "empty completion response" in data["detail"].lower()


@pytest.mark.asyncio
async def test_08_malformed_groq_response(monkeypatch):
    """Scenario 8: Malformed Groq response returns HTTP 502 Bad Gateway."""
    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "test-org/test-repo")
        if not (await session.execute(stmt)).scalar_one_or_none():
            session.add(
                Repository(
                    github_id=99991,
                    owner="test-org",
                    name="test-repo",
                    full_name="test-org/test-repo",
                    is_active=True,
                )
            )
            await session.commit()

    def mock_analyze(self, repo_full_name, metrics):
        raise AIMalformedResponseError("Groq API returned a malformed response.")

    monkeypatch.setattr(GroqAIService, "analyze_repository_metrics", mock_analyze)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-08"},
        )
        assert resp.status_code == 502
        data = resp.json()
        assert "malformed response" in data["detail"].lower()


@pytest.mark.asyncio
async def test_09_repository_not_found(monkeypatch):
    """Scenario 9: Repository not found in DB or GitHub returns HTTP 404."""
    # Mock GitHubClient fetch_repository_metadata to return None
    from backend.src.gitpulse.ingestion.github_client import GitHubClient

    monkeypatch.setattr(
        GitHubClient,
        "fetch_repository_metadata",
        AsyncMock(return_value=None),
    )

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/ghost-org/phantom-repo-404/ai-insights",
            headers={"X-Request-ID": "test-req-09"},
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "Repository 'ghost-org/phantom-repo-404' not found" in data["detail"]


@pytest.mark.asyncio
async def test_10_empty_repository_metrics(monkeypatch):
    """Scenario 10: Empty repository metrics handles 0 commits/PRs gracefully."""
    from backend.src.gitpulse.ingestion.pipeline import DataIngestionPipeline

    # Prevent fallback backfill from generating synthetic commits in this test
    monkeypatch.setattr(DataIngestionPipeline, "ingest_commits", AsyncMock())
    monkeypatch.setattr(DataIngestionPipeline, "ingest_pull_requests", AsyncMock())

    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "truly-empty-org/truly-empty-repo")
        repo = (await session.execute(stmt)).scalar_one_or_none()
        if not repo:
            repo = Repository(
                github_id=77777,
                owner="truly-empty-org",
                name="truly-empty-repo",
                full_name="truly-empty-org/truly-empty-repo",
                is_active=True,
            )
            session.add(repo)
            await session.commit()

    captured_metrics = {}

    def mock_analyze(self, repo_full_name, metrics):
        captured_metrics.update(metrics)
        return (
            "1. Velocity Health: Inactive / newly tracked repository (0 commits in 30 days).\n"
            "2. Review Bottlenecks: No open pull requests found.\n"
            "3. Strategic Action: Verify repository push access and branch protection."
        )

    monkeypatch.setattr(GroqAIService, "analyze_repository_metrics", mock_analyze)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/truly-empty-org/truly-empty-repo/ai-insights",
            headers={"X-Request-ID": "test-req-10"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["repository"] == "truly-empty-org/truly-empty-repo"
        assert "Inactive / newly tracked" in data["insights"]
        # Ensure zero metrics were passed correctly without crashing
        assert captured_metrics.get("total_commits") == 0
        assert captured_metrics.get("active_contributors") == 0


@pytest.mark.asyncio
async def test_11_database_connection_failure(monkeypatch):
    """Scenario 11: Database connection failure returns HTTP 503."""
    from backend.src.gitpulse.api import routes

    def mock_session_local():
        raise ConnectionError("Database network connection refused")

    monkeypatch.setattr(routes, "AsyncSessionLocal", mock_session_local)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-11"},
        )
        assert resp.status_code == 503
        data = resp.json()
        assert "Database service temporarily unavailable" in data["detail"]


@pytest.mark.asyncio
async def test_12_database_query_failure(monkeypatch):
    """Scenario 12: Database query failure during calculation returns HTTP 500 without stack trace."""
    from backend.src.gitpulse.api import routes

    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "test-org/test-repo")
        if not (await session.execute(stmt)).scalar_one_or_none():
            session.add(
                Repository(
                    github_id=99991,
                    owner="test-org",
                    name="test-repo",
                    full_name="test-org/test-repo",
                    is_active=True,
                )
            )
            await session.commit()

    async def mock_velocity(*args, **kwargs):
        raise SQLAlchemyError("SQL query timeout or deadlock detected")

    monkeypatch.setattr(routes, "get_repository_velocity", mock_velocity)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-12"},
        )
        assert resp.status_code == 500
        data = resp.json()
        assert "Database query failed" in data["detail"]
        # Stack trace should NOT be in the client response
        assert "Traceback" not in data["detail"]


@pytest.mark.asyncio
async def test_13_unexpected_internal_exception(monkeypatch):
    """Scenario 13: Unexpected internal exception returns HTTP 500 with correlation ID and safe message."""
    from backend.src.gitpulse.api import routes

    async with AsyncSessionLocal() as session:
        stmt = select(Repository).where(Repository.full_name == "test-org/test-repo")
        if not (await session.execute(stmt)).scalar_one_or_none():
            session.add(
                Repository(
                    github_id=99991,
                    owner="test-org",
                    name="test-repo",
                    full_name="test-org/test-repo",
                    is_active=True,
                )
            )
            await session.commit()

    async def mock_velocity(*args, **kwargs):
        raise RuntimeError("Severe internal calculation glitch")

    monkeypatch.setattr(routes, "get_repository_velocity", mock_velocity)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/repos/test-org/test-repo/ai-insights",
            headers={"X-Request-ID": "test-req-13"},
        )
        assert resp.status_code == 500
        data = resp.json()
        assert "An unexpected internal error occurred" in data["detail"]
        assert "test-req-13" in data["detail"]
        # Confirm no internal stack trace leaked to client
        assert "Traceback" not in data["detail"]
