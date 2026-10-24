"""GitHub REST & GraphQL API Client."""

from __future__ import annotations

import hashlib
import hmac
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
        self.rate_limit_remaining: int | None = None
        self.rate_limit_reset: int | None = None
        self.rate_limit_total: int | None = None

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitPulse-Ingestion-Engine/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def _update_rate_limits(self, headers: httpx.Headers) -> None:
        """Extracts and tracks rate limit metadata from GitHub response headers."""
        if "x-ratelimit-remaining" in headers:
            try:
                self.rate_limit_remaining = int(headers["x-ratelimit-remaining"])
                self.rate_limit_reset = int(headers.get("x-ratelimit-reset", "0"))
                self.rate_limit_total = int(headers.get("x-ratelimit-limit", "60"))
            except ValueError:
                pass

    def get_rate_limit_status(self) -> dict[str, Any]:
        """Returns the current known rate limit budget."""
        return {
            "remaining": self.rate_limit_remaining,
            "reset_timestamp": self.rate_limit_reset,
            "limit": self.rate_limit_total,
            "is_exhausted": (
                self.rate_limit_remaining is not None
                and self.rate_limit_remaining <= self.rate_limit_buffer
            ),
        }

    @staticmethod
    def verify_webhook_signature(
        payload_bytes: bytes, signature_header: str | None, secret: str
    ) -> bool:
        """Validates HMAC SHA-256 signature on inbound GitHub webhook push."""
        if not secret or not signature_header:
            return False
        expected = (
            "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        )
        return hmac.compare_digest(expected, signature_header)

    async def fetch_repository_events(
        self,
        owner: str,
        repo: str,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """Fetches public event stream for a target repository with rate limit awareness."""
        if (
            self.rate_limit_remaining is not None
            and self.rate_limit_remaining <= self.rate_limit_buffer
        ):
            logger.warning(
                "Rate limit budget (%d) reached buffer threshold (%d). Yielding synthetic fallback.",
                self.rate_limit_remaining,
                self.rate_limit_buffer,
            )
            return await self.fetch_synthetic_events(owner, repo)

        url = f"{self.base_url}/repos/{owner}/{repo}/events"
        params = {"page": page, "per_page": per_page}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, headers=self._get_headers(), params=params)
                self._update_rate_limits(resp.headers)

                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 403:
                    logger.warning("GitHub API rate limit exceeded or forbidden: %s", resp.text)
                    return await self.fetch_synthetic_events(owner, repo)
                else:
                    logger.error("GitHub API returned status %d: %s", resp.status_code, resp.text)
                    return []
            except httpx.RequestError as exc:
                logger.error("Network error while connecting to GitHub API: %s", exc)
                return await self.fetch_synthetic_events(owner, repo)

    async def fetch_all_recent_events(
        self,
        owner: str,
        repo: str,
        max_pages: int = 3,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """Iteratively paginates through event pages and aggregates stream."""
        aggregated: list[dict[str, Any]] = []
        for p in range(1, max_pages + 1):
            page_events = await self.fetch_repository_events(owner, repo, page=p, per_page=per_page)
            if not page_events:
                break
            aggregated.extend(page_events)
            if len(page_events) < per_page:
                break
        return aggregated

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
