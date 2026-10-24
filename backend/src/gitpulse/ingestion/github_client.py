"""GitHub REST & GraphQL API Client."""

from __future__ import annotations

from typing import Any

import httpx

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger


class GitHubClient:
    """Ingestion client for fetching activity streams from GitHub API."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        rate_limit_buffer: int = 100,
    ):
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = (base_url or settings.GITHUB_API_BASE_URL).rstrip("/")
        self.rate_limit_buffer = rate_limit_buffer

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitPulse-Ingestion-Engine/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def fetch_repository_events(
        self,
        owner: str,
        repo: str,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """Fetches public event stream for a target repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/events"
        params = {"page": page, "per_page": per_page}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, headers=self._get_headers(), params=params)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 403:
                    logger.warning("GitHub API rate limit exceeded or forbidden: %s", resp.text)
                    return []
                else:
                    logger.error("GitHub API returned status %d: %s", resp.status_code, resp.text)
                    return []
            except httpx.RequestError as exc:
                logger.error("Network error while connecting to GitHub API: %s", exc)
                return []

    async def fetch_synthetic_events(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Generates realistic synthetic GitHub events for hermetic local simulation."""
        return [
            {
                "id": "evt_1001",
                "type": "PushEvent",
                "actor": {
                    "login": "octocat",
                    "avatar_url": "https://avatars.githubusercontent.com/u/583231",
                },
                "repo": {"name": f"{owner}/{repo}"},
                "payload": {
                    "commits": [{"sha": "abc1234", "message": "feat: add streaming connector"}]
                },
                "created_at": "2026-10-24T18:00:00Z",
            },
            {
                "id": "evt_1002",
                "type": "PullRequestEvent",
                "actor": {
                    "login": "alice-dev",
                    "avatar_url": "https://avatars.githubusercontent.com/u/102938",
                },
                "repo": {"name": f"{owner}/{repo}"},
                "payload": {
                    "action": "opened",
                    "pull_request": {"number": 42, "title": "fix: resolve deadlock"},
                },
                "created_at": "2026-10-24T18:30:00Z",
            },
        ]
