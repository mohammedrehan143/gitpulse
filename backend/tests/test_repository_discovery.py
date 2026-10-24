"""Tests for Automatic Repository Discovery and Monitoring Service."""

from __future__ import annotations

import httpx
import pytest

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.services.repository_service import RepositoryService


@pytest.mark.asyncio
async def test_discover_owned_repositories_pagination(monkeypatch):
    """Verifies that discovery paginates through /user/repos until all pages are retrieved."""
    client = GitHubClient(token="ghp_testToken123")

    page_1_repos = [
        {
            "id": 1000 + i,
            "name": f"repo-{i}",
            "full_name": f"test-user/repo-{i}",
            "owner": {"login": "test-user", "type": "User"},
            "description": f"Test repo {i}",
            "visibility": "public",
            "default_branch": "main",
            "html_url": f"https://github.com/test-user/repo-{i}",
            "created_at": "2026-01-01T00:00:00Z",
            "pushed_at": "2026-10-24T12:00:00Z",
            "stargazers_count": 5,
            "forks_count": 1,
        }
        for i in range(100)
    ]

    page_2_repos = [
        {
            "id": 2000 + i,
            "name": f"repo-p2-{i}",
            "full_name": f"test-user/repo-p2-{i}",
            "owner": {"login": "test-user", "type": "User"},
            "description": f"Test repo page 2 {i}",
            "visibility": "private",
            "private": True,
            "default_branch": "main",
            "html_url": f"https://github.com/test-user/repo-p2-{i}",
            "created_at": "2026-02-01T00:00:00Z",
            "pushed_at": "2026-10-24T14:00:00Z",
            "stargazers_count": 2,
            "forks_count": 0,
        }
        for i in range(25)
    ]

    async def mock_get(self, url, headers=None, params=None):
        req = httpx.Request("GET", url)
        if "/user/repos" in url:
            page = (params or {}).get("page", 1)
            if page == 1:
                return httpx.Response(200, json=page_1_repos, request=req)
            elif page == 2:
                return httpx.Response(200, json=page_2_repos, request=req)
            else:
                return httpx.Response(200, json=[], request=req)
        elif "/user" in url:
            return httpx.Response(200, json={"login": "test-user", "id": 9999}, request=req)
        return httpx.Response(404, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    discovered = await client.discover_owned_repositories()
    assert len(discovered) == 125
    assert discovered[0]["full_name"] == "test-user/repo-0"
    assert discovered[100]["full_name"] == "test-user/repo-p2-0"
    assert discovered[100]["visibility"] == "private"


@pytest.mark.asyncio
async def test_discover_owner_filtering(monkeypatch):
    """Verifies that non-owned and organization repositories are excluded."""
    client = GitHubClient(token="ghp_testToken123")

    mixed_repos = [
        # 1. Owned by authenticated user
        {
            "id": 101,
            "name": "my-owned-repo",
            "full_name": "rehan/my-owned-repo",
            "owner": {"login": "rehan", "type": "User"},
            "visibility": "public",
        },
        # 2. Contributed/collaborator repo owned by another user
        {
            "id": 102,
            "name": "collaborator-repo",
            "full_name": "other-user/collaborator-repo",
            "owner": {"login": "other-user", "type": "User"},
            "visibility": "public",
        },
        # 3. Organization-owned repo
        {
            "id": 103,
            "name": "org-project",
            "full_name": "apache/org-project",
            "owner": {"login": "apache", "type": "Organization"},
            "visibility": "public",
        },
    ]

    async def mock_get(self, url, headers=None, params=None):
        req = httpx.Request("GET", url)
        if "/user/repos" in url:
            return httpx.Response(200, json=mixed_repos, request=req)
        elif "/user" in url:
            return httpx.Response(200, json={"login": "rehan"}, request=req)
        return httpx.Response(404, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    discovered = await client.discover_owned_repositories()
    assert len(discovered) == 1
    assert discovered[0]["full_name"] == "rehan/my-owned-repo"
    assert discovered[0]["owner"] == "rehan"


@pytest.mark.asyncio
async def test_discover_private_repository_permissions(monkeypatch):
    """Verifies that private repositories with token permissions are correctly identified."""
    client = GitHubClient(token="ghp_testToken123")

    repos = [
        {
            "id": 201,
            "name": "secret-service",
            "full_name": "rehan/secret-service",
            "owner": {"login": "rehan", "type": "User"},
            "private": True,
            "visibility": "private",
            "default_branch": "dev",
            "html_url": "https://github.com/rehan/secret-service",
        }
    ]

    async def mock_get(self, url, headers=None, params=None):
        req = httpx.Request("GET", url)
        if "/user/repos" in url:
            return httpx.Response(200, json=repos, request=req)
        elif "/user" in url:
            return httpx.Response(200, json={"login": "rehan"}, request=req)
        return httpx.Response(404, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    discovered = await client.discover_owned_repositories()
    assert len(discovered) == 1
    assert discovered[0]["visibility"] == "private"
    assert discovered[0]["default_branch"] == "dev"


@pytest.mark.asyncio
async def test_discover_rate_limit_fallback():
    """Verifies that rate limit threshold triggers synthetic fallback safely."""
    client = GitHubClient(token="ghp_testToken123", rate_limit_buffer=100)
    client.rate_limit_remaining = 50  # Below 100 buffer

    discovered = await client.discover_owned_repositories()
    # Must yield synthetic fallback without crashing
    assert len(discovered) >= 2
    assert any(r["visibility"] == "private" for r in discovered)


@pytest.mark.asyncio
async def test_repository_service_sync_and_duplicate_prevention(monkeypatch):
    """Verifies that multiple syncs upsert without duplicating records and update attributes."""
    sample_repos = [
        {
            "id": 301,
            "name": "alpha",
            "full_name": "test-sync/alpha",
            "owner": "test-sync",
            "description": "Initial description",
            "visibility": "public",
            "default_branch": "main",
            "html_url": "https://github.com/test-sync/alpha",
            "created_at": "2026-01-01T00:00:00Z",
            "pushed_at": "2026-10-24T10:00:00Z",
            "stars_count": 10,
            "forks_count": 2,
            "is_active": True,
            "monitoring_status": "POLLING",
        }
    ]

    client = GitHubClient(token="")
    monkeypatch.setattr(client, "discover_owned_repositories", lambda: _async_return(sample_repos))
    service = RepositoryService(client=client)

    # 1. First sync
    res1 = await service.sync_repositories()
    alpha1 = next((r for r in res1 if r["full_name"] == "test-sync/alpha"), None)
    assert alpha1 is not None
    assert alpha1["description"] == "Initial description"

    # 2. Second sync with updated attributes
    sample_repos[0]["description"] = "Updated description after refactor"
    sample_repos[0]["stars_count"] = 15
    res2 = await service.sync_repositories()

    # Verify no duplicate was created for test-sync/alpha
    matching = [r for r in res2 if r["full_name"] == "test-sync/alpha"]
    assert len(matching) == 1
    assert matching[0]["description"] == "Updated description after refactor"
    assert matching[0]["stars_count"] == 15


@pytest.mark.asyncio
async def test_repository_service_detect_deleted_or_inaccessible(monkeypatch):
    """Verifies that deleted or removed repositories are marked INACCESSIBLE without deletion."""
    inventory_step_1 = [
        {
            "id": 401,
            "name": "active-repo",
            "full_name": "test-del/active-repo",
            "owner": "test-del",
            "visibility": "public",
            "default_branch": "main",
            "is_active": True,
            "monitoring_status": "POLLING",
        },
        {
            "id": 402,
            "name": "soon-deleted-repo",
            "full_name": "test-del/soon-deleted-repo",
            "owner": "test-del",
            "visibility": "public",
            "default_branch": "main",
            "is_active": True,
            "monitoring_status": "POLLING",
        },
    ]

    client = GitHubClient(token="")
    monkeypatch.setattr(
        client, "discover_owned_repositories", lambda: _async_return(inventory_step_1)
    )
    service = RepositoryService(client=client)

    # Step 1: Sync both repos
    await service.sync_repositories()

    # Step 2: Next sync has only active-repo (soon-deleted-repo was deleted or lost access)
    inventory_step_2 = [inventory_step_1[0]]
    monkeypatch.setattr(
        client, "discover_owned_repositories", lambda: _async_return(inventory_step_2)
    )

    res = await service.sync_repositories()
    deleted_repo = next((r for r in res if r["full_name"] == "test-del/soon-deleted-repo"), None)

    assert deleted_repo is not None
    assert deleted_repo["is_active"] is False
    assert deleted_repo["monitoring_status"] == "INACCESSIBLE"


@pytest.mark.asyncio
async def test_manual_configuration_fallback(monkeypatch):
    """Verifies fallback to GITHUB_TARGET_REPOS when auto discovery is disabled."""
    monkeypatch.setattr(settings, "AUTO_DISCOVER_REPOSITORIES", False)
    monkeypatch.setattr(settings, "GITHUB_TARGET_REPOS", "custom/repo-one,custom/repo-two")

    service = RepositoryService()
    repos = await service.sync_repositories()

    names = [r["full_name"] for r in repos]
    assert "custom/repo-one" in names
    assert "custom/repo-two" in names


async def _async_return(val):
    return val
