"""Repository Management and Discovery Service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import Repository


def _parse_iso_datetime(val: Any) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _upsert_repo_record(
    session: AsyncSession,
    full_name: str,
    data: dict[str, Any],
    existing_repos: dict[str, Repository],
    now: datetime,
) -> None:
    owner, name = full_name.split("/", 1)
    pushed_dt = _parse_iso_datetime(data.get("pushed_at"))

    if full_name in existing_repos:
        repo_obj = existing_repos[full_name]
        repo_obj.description = data.get("description")
        repo_obj.visibility = data.get("visibility", "public")
        repo_obj.default_branch = data.get("default_branch", "main")
        repo_obj.html_url = data.get("html_url")
        if pushed_dt:
            repo_obj.pushed_at = pushed_dt
        repo_obj.is_active = True
        repo_obj.monitoring_status = data.get("monitoring_status", "POLLING")
        repo_obj.last_synced_at = now
        repo_obj.stars_count = data.get("stars_count", 0)
        repo_obj.forks_count = data.get("forks_count", 0)
    else:
        new_repo = Repository(
            github_id=data.get("id") or (abs(hash(full_name)) % 10000000),
            owner=owner,
            name=name,
            full_name=full_name,
            description=data.get("description"),
            visibility=data.get("visibility", "public"),
            default_branch=data.get("default_branch", "main"),
            html_url=data.get("html_url") or f"https://github.com/{full_name}",
            pushed_at=pushed_dt,
            is_active=True,
            monitoring_status=data.get("monitoring_status", "POLLING"),
            last_synced_at=now,
            stars_count=data.get("stars_count", 0),
            forks_count=data.get("forks_count", 0),
        )
        session.add(new_repo)


def _mark_missing_repos_inaccessible(
    existing_repos: dict[str, Repository],
    discovered_names: set[str],
    now: datetime,
) -> None:
    for full_name, existing_repo in existing_repos.items():
        if full_name not in discovered_names and existing_repo.is_active:
            logger.info("Repository %s no longer in inventory. Marking as INACCESSIBLE.", full_name)
            existing_repo.is_active = False
            existing_repo.monitoring_status = "INACCESSIBLE"
            existing_repo.last_synced_at = now


class RepositoryService:
    """Service managing discovery, persistence, and monitoring status of repositories."""

    _cached_repositories: list[dict[str, Any]] = []

    def __init__(self, client: GitHubClient | None = None):
        self.client = client or GitHubClient()

    async def _fetch_raw_inventory(self) -> list[dict[str, Any]]:
        """Discovers repositories via GitHub API or returns manual fallback."""
        if settings.AUTO_DISCOVER_REPOSITORIES:
            try:
                discovered = await self.client.discover_owned_repositories()
                if discovered:
                    return discovered
            except Exception as exc:
                logger.error("Error during automatic repository discovery: %s", exc)

        logger.info("Using manual target repositories fallback: %s", settings.GITHUB_TARGET_REPOS)
        return self._generate_fallback_repositories()

    async def sync_repositories(self) -> list[dict[str, Any]]:
        """Synchronizes repository inventory from GitHub API or fallback configuration."""
        discovered_raw = await self._fetch_raw_inventory()
        now = datetime.now(UTC)
        discovered_by_fullname = {r["full_name"]: r for r in discovered_raw}

        try:
            await init_db()
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    stmt = select(Repository)
                    result = await session.execute(stmt)
                    existing_repos = {repo.full_name: repo for repo in result.scalars().all()}

                    for full_name, data in discovered_by_fullname.items():
                        _upsert_repo_record(session, full_name, data, existing_repos, now)

                    _mark_missing_repos_inaccessible(
                        existing_repos, set(discovered_by_fullname.keys()), now
                    )
                    await session.flush()

                refreshed_stmt = select(Repository).order_by(Repository.full_name)
                refreshed_result = await session.execute(refreshed_stmt)
                persisted_repos = refreshed_result.scalars().all()

                RepositoryService._cached_repositories = [
                    {
                        "id": r.id,
                        "github_id": r.github_id,
                        "owner": r.owner,
                        "name": r.name,
                        "full_name": r.full_name,
                        "description": r.description,
                        "visibility": r.visibility,
                        "default_branch": r.default_branch,
                        "html_url": r.html_url,
                        "pushed_at": r.pushed_at.isoformat() if r.pushed_at else None,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "is_active": r.is_active,
                        "monitoring_status": r.monitoring_status,
                        "last_synced_at": (
                            r.last_synced_at.isoformat() if r.last_synced_at else None
                        ),
                        "stars_count": r.stars_count,
                        "forks_count": r.forks_count,
                    }
                    for r in persisted_repos
                ]
        except Exception as db_exc:
            logger.warning("Database unavailable (%s). Using in-memory cache.", db_exc)
            existing_cache = {
                r["full_name"]: dict(r) for r in RepositoryService._cached_repositories
            }
            for d in discovered_raw:
                fn = d["full_name"]
                existing_cache[fn] = {
                    **d,
                    "github_id": d.get("github_id") or d.get("id") or 0,
                    "last_synced_at": now.isoformat(),
                    "is_active": True,
                }
            for fn, r in existing_cache.items():
                if fn not in discovered_by_fullname and r.get("is_active", True):
                    r["is_active"] = False
                    r["monitoring_status"] = "INACCESSIBLE"
                    r["last_synced_at"] = now.isoformat()
            RepositoryService._cached_repositories = list(existing_cache.values())

        return list(RepositoryService._cached_repositories)

    def _generate_fallback_repositories(self) -> list[dict[str, Any]]:
        """Generates fallback repository entries from GITHUB_TARGET_REPOS."""
        repos = []
        target_list = [r.strip() for r in settings.GITHUB_TARGET_REPOS.split(",") if r.strip()]
        for idx, target in enumerate(target_list, start=1):
            parts = target.split("/")
            if len(parts) == 2:
                owner, name = parts[0], parts[1]
                repos.append(
                    {
                        "id": 100000 + idx,
                        "github_id": 100000 + idx,
                        "name": name,
                        "full_name": target,
                        "owner": owner,
                        "description": f"Repository monitored via fallback configuration ({target})",
                        "visibility": "public",
                        "default_branch": "main",
                        "html_url": f"https://github.com/{target}",
                        "created_at": "2026-01-01T00:00:00Z",
                        "pushed_at": datetime.now(UTC).isoformat(),
                        "stars_count": 0,
                        "forks_count": 0,
                        "is_active": True,
                        "monitoring_status": "FALLBACK_CONFIG",
                    }
                )
        return repos

    async def get_all_repositories(self) -> list[dict[str, Any]]:
        """Returns all repositories in inventory."""
        if not RepositoryService._cached_repositories:
            await self.sync_repositories()
        return list(RepositoryService._cached_repositories)

    async def get_monitored_repositories(self) -> list[dict[str, Any]]:
        """Returns only actively monitored repositories."""
        all_repos = await self.get_all_repositories()
        return [r for r in all_repos if r.get("is_active", True)]

    async def get_target_repo_names(self) -> list[str]:
        """Returns string list of full names of monitored repositories."""
        active = await self.get_monitored_repositories()
        return [r["full_name"] for r in active]
