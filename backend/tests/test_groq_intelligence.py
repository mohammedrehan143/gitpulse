"""Comprehensive Tests for Groq AI Engineering Intelligence Service and API Endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.src.gitpulse.api.main import app
from backend.src.gitpulse.services.groq_intelligence_service import (
    GroqIntelligenceService,
    groq_intelligence_service,
)
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import (
    CommitRecord,
    ContributorRecord,
    PullRequestRecord,
    Repository,
    ReviewRecord,
)

TEST_OWNER = "ai-intel-test"
TEST_REPO = "sample-repo"
TEST_FULL_NAME = f"{TEST_OWNER}/{TEST_REPO}"


@pytest.fixture(autouse=True)
async def seed_test_database():
    """Ensure database schema is initialized and fast deterministic records are present."""
    await init_db()
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing = (
            await session.execute(select(Repository).where(Repository.full_name == TEST_FULL_NAME))
        ).scalar_one_or_none()
        if not existing:
            repo = Repository(
                github_id=99988877,
                owner=TEST_OWNER,
                name=TEST_REPO,
                full_name=TEST_FULL_NAME,
                description="Test repository for Groq AI Engineering Intelligence",
                visibility="public",
                default_branch="main",
                html_url=f"https://github.com/{TEST_FULL_NAME}",
                is_active=True,
                stars_count=42,
                forks_count=7,
                last_synced_at=datetime.now(UTC),
                pushed_at=datetime.now(UTC),
            )
            session.add(repo)
            await session.flush()

            # Seed 5 commits
            now = datetime.now(UTC)
            for i in range(5):
                c = CommitRecord(
                    repo_id=repo.id,
                    sha=f"sha_intel_{i}_{datetime.now().timestamp()}",
                    message=f"feat(core): intelligent test commit #{i}",
                    author_name="lead-dev",
                    author_email="dev@example.com",
                    committed_at=now - timedelta(days=i),
                    lines_added=120,
                    lines_deleted=30,
                )
                session.add(c)

            # Seed 2 PRs (one open, one merged)
            pr1 = PullRequestRecord(
                repo_id=repo.id,
                github_id=990001,
                number=1,
                title="feat: implement engineering intelligence pipeline",
                body="Full pipeline ingestion and analytics grounding",
                state="open",
                author_login="lead-dev",
                created_at=now - timedelta(days=10),  # Long-running > 7 days
                first_reviewed_at=now - timedelta(days=8),
                additions=650,
                deletions=120,
                changed_files=15,
                review_comments_count=4,
            )
            pr2 = PullRequestRecord(
                repo_id=repo.id,
                github_id=990002,
                number=2,
                title="fix: resolve datetime offset subtraction",
                body="Normalize timezone before arithmetic",
                state="closed",
                author_login="senior-eng",
                created_at=now - timedelta(days=3),
                merged_at=now - timedelta(days=2),
                first_reviewed_at=now - timedelta(days=2, hours=12),
                additions=45,
                deletions=12,
                changed_files=2,
                review_comments_count=1,
            )
            session.add(pr1)
            session.add(pr2)
            await session.flush()

            # Seed reviews
            rev = ReviewRecord(
                pr_id=pr1.id,
                github_id=880001,
                reviewer_login="code-reviewer",
                state="APPROVED",
                submitted_at=now - timedelta(days=8),
                body="Looks solid and well tested.",
            )
            session.add(rev)

            # Seed Contributor
            contrib = ContributorRecord(
                repo_id=repo.id,
                login="lead-dev",
                name="Lead Developer",
                contributions_count=25,
                commits_count=18,
                prs_count=5,
                issues_count=2,
                first_contributed_at=now - timedelta(days=60),
                last_contributed_at=now,
            )
            session.add(contrib)

            await session.commit()


@pytest.mark.asyncio
async def test_repository_intelligence_grounding_and_cache():
    """Tests repository intelligence generation, grounded facts, and TTL caching."""
    service = GroqIntelligenceService(
        api_key=""
    )  # Explicitly disabled API key for deterministic test

    # First run: fresh calculation
    res1 = await service.generate_repository_intelligence(TEST_OWNER, TEST_REPO, timeframe_days=30)
    assert "error" not in res1
    assert res1["repository"] == TEST_FULL_NAME
    assert res1["cached"] is False
    assert "verified_facts" in res1
    assert res1["verified_facts"]["total_commits"] >= 5
    assert res1["verified_facts"]["long_running_prs_count"] >= 1
    assert "health_summary" in res1
    assert "strategic_recommendations" in res1
    assert "ai_interpretations" in res1
    assert "missing_or_unavailable" in res1

    # Second run: cached retrieval
    res2 = await service.generate_repository_intelligence(TEST_OWNER, TEST_REPO, timeframe_days=30)
    assert res2["cached"] is True
    assert res2["repository"] == res1["repository"]

    # Force refresh
    res3 = await service.generate_repository_intelligence(
        TEST_OWNER, TEST_REPO, timeframe_days=30, force_refresh=True
    )
    assert res3["cached"] is False


@pytest.mark.asyncio
async def test_pr_intelligence_complexity_and_risk():
    """Tests pull request complexity analysis, risk scoring, and grounded metrics."""
    service = GroqIntelligenceService(api_key="")

    res = await service.generate_pr_intelligence(TEST_OWNER, TEST_REPO, pr_number=1)
    assert "error" not in res
    assert res["number"] == 1
    assert res["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "verified_metrics" in res
    assert "pr_summary" in res
    assert "recommendations" in res
    assert res["verified_metrics"]["changed_files"] == 15


@pytest.mark.asyncio
async def test_developer_intelligence_evidence_based():
    """Tests developer intelligence to ensure strictly evidence-based metrics without subjective scores."""
    service = GroqIntelligenceService(api_key="")

    res = await service.generate_developer_intelligence(TEST_OWNER, TEST_REPO, "lead-dev")
    assert "error" not in res
    assert res["developer"] == "lead-dev"
    assert "verified_metrics" in res
    assert "contribution_summary" in res
    assert "evidence_notes" in res
    # Verify no ungrounded scores
    assert "score" not in res
    assert "grade" not in res


@pytest.mark.asyncio
async def test_team_intelligence_weekly_report():
    """Tests weekly team engineering report, review bottlenecks, and collaboration patterns."""
    service = GroqIntelligenceService(api_key="")

    res = await service.generate_team_intelligence(TEST_OWNER, TEST_REPO, timeframe_days=7)
    assert "error" not in res
    assert "weekly_report" in res
    assert "review_bottlenecks" in res
    assert "collaboration_patterns" in res
    assert "team_recommendations" in res


@pytest.mark.asyncio
async def test_ai_engineering_assistant_qa():
    """Tests natural language question answering with grounded context retrieval."""
    service = GroqIntelligenceService(api_key="")

    # Query 1: Longest open PRs
    q1 = await service.query_engineering_assistant("Which PRs have been open the longest?")
    assert "answer" in q1
    assert "verified_facts" in q1
    assert "timeframe" in q1

    # Query 2: Inactive repositories
    q2 = await service.query_engineering_assistant("Which repositories have been inactive?")
    assert "answer" in q2
    assert "inactive" in q2["answer"].lower() or "monitored" in q2["answer"].lower()

    # Query 3: Who contributed most recently?
    q3 = await service.query_engineering_assistant("Who contributed most recently?")
    assert "answer" in q3
    assert len(q3["answer"]) > 10

    # Query 4: Weekly summary
    q4 = await service.query_engineering_assistant("What happened in my repositories this week?")
    assert "answer" in q4
    assert "commits" in q4["answer"].lower()


@pytest.mark.asyncio
async def test_groq_api_call_and_failure_resilience():
    """Tests that Groq API exceptions are caught gracefully and seamlessly fall back to grounded engine."""
    service = GroqIntelligenceService(api_key="mock_key_123")

    # Mock client chat.completions.create to simulate rate-limit / timeout error
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError(
        "Groq Rate Limit Exceeded: 429 Too Many Requests"
    )

    with patch.object(service, "_client", mock_client):
        res = await service.generate_repository_intelligence(
            TEST_OWNER, TEST_REPO, force_refresh=True
        )
        assert "error" not in res
        assert res["source"] == "grounded_rule_engine"
        assert "health_summary" in res
        assert res["verified_facts"]["total_commits"] > 0


@pytest.mark.asyncio
async def test_ai_api_endpoints():
    """Tests all FastAPI endpoints under /api/v1/ai."""
    with patch.object(groq_intelligence_service, "_call_groq_json", return_value=None):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Repository Overview
            r1 = await client.get(
                f"/api/v1/ai/repos/{TEST_OWNER}/{TEST_REPO}/overview?timeframe=30d"
            )
            assert r1.status_code == 200
            d1 = r1.json()
            assert d1["repository"] == TEST_FULL_NAME

            # 2. PR Intelligence
            r2 = await client.get(f"/api/v1/ai/repos/{TEST_OWNER}/{TEST_REPO}/prs/1")
            assert r2.status_code == 200
            d2 = r2.json()
            assert d2["number"] == 1

            # 3. Developer Intelligence
            r3 = await client.get(f"/api/v1/ai/repos/{TEST_OWNER}/{TEST_REPO}/developers/lead-dev")
            assert r3.status_code == 200
            d3 = r3.json()
            assert d3["developer"] == "lead-dev"

            # 4. Team Report
            r4 = await client.get(
                f"/api/v1/ai/repos/{TEST_OWNER}/{TEST_REPO}/team-report?timeframe=7d"
            )
            assert r4.status_code == 200
            d4 = r4.json()
            assert "weekly_report" in d4

            # 5. Assistant Chat
            r5 = await client.post(
                "/api/v1/ai/assistant/chat",
                json={
                    "question": "What is the status of my repositories?",
                    "target_repo": TEST_FULL_NAME,
                },
            )
            assert r5.status_code == 200
            d5 = r5.json()
            assert "answer" in d5
            assert len(d5["answer"]) > 0
