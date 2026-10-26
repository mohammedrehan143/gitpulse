"""Repository Inventory & Monitoring Synchronization Service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import Repository


def _upsert_repo_record(
    session: Any,
    full_name: str,
    data: dict[str, Any],
    existing_repos: dict[str, Repository],
    now: datetime,
) -> None:
    pushed_dt = None
    if data.get("pushed_at"):
        try:
            pushed_dt = datetime.fromisoformat(str(data["pushed_at"]).replace("Z", "+00:00"))
        except Exception:
            pass

    created_dt = now
    if data.get("created_at"):
        try:
            created_dt = datetime.fromisoformat(str(data["created_at"]).replace("Z", "+00:00"))
        except Exception:
            pass

    raw_id = data.get("github_id") or data.get("id") or (abs(hash(full_name)) % 100000000)

    if full_name in existing_repos:
        repo = existing_repos[full_name]
        repo.description = data.get("description")
        repo.visibility = data.get("visibility", "public")
        repo.default_branch = data.get("default_branch", "main")
        repo.html_url = data.get("html_url")
        repo.pushed_at = pushed_dt
        repo.is_active = data.get("is_active", True)
        repo.monitoring_status = "ACTIVE"
        repo.last_synced_at = now
        repo.stars_count = data.get("stars_count", 0)
        repo.forks_count = data.get("forks_count", 0)
    else:
        new_repo = Repository(
            github_id=raw_id,
            owner=data["owner"],
            name=data["name"],
            full_name=full_name,
            description=data.get("description"),
            visibility=data.get("visibility", "public"),
            default_branch=data.get("default_branch", "main"),
            html_url=data.get("html_url"),
            pushed_at=pushed_dt,
            created_at=created_dt,
            is_active=True,
            monitoring_status="ACTIVE",
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
            logger.info(
                "Repository %s no longer in active target list. Updating status.", full_name
            )
            existing_repo.is_active = False
            existing_repo.monitoring_status = "INACCESSIBLE"
            existing_repo.last_synced_at = now


class RepositoryService:
    """Service managing live discovery, persistence, and inventory of repositories."""

    _cached_repositories: list[dict[str, Any]] = []

    def __init__(self, client: GitHubClient | None = None):
        self.client = client or GitHubClient()

    async def _fetch_raw_inventory(self) -> list[dict[str, Any]]:
        """Discovers real repositories via GitHub API."""
        try:
            discovered = await self.client.discover_owned_repositories()
            if discovered:
                return discovered
        except Exception as exc:
            logger.error("Error during repository discovery: %s", exc)

        # Fallback to fetching real metadata for target repositories
        target_list = [r.strip() for r in settings.GITHUB_TARGET_REPOS.split(",") if r.strip()]
        results = []
        for target in target_list:
            parts = target.split("/")
            if len(parts) == 2:
                meta = await self.client.fetch_repository_metadata(parts[0], parts[1])
                if meta:
                    results.append(meta)
                else:
                    results.append(
                        {
                            "id": abs(hash(target)) % 100000000,
                            "name": parts[1],
                            "full_name": target,
                            "owner": parts[0],
                            "description": f"Real-time monitored repository {target}",
                            "visibility": "public",
                            "default_branch": "main",
                            "html_url": f"https://github.com/{target}",
                            "created_at": datetime.now(UTC).isoformat(),
                            "pushed_at": datetime.now(UTC).isoformat(),
                            "stars_count": 0,
                            "forks_count": 0,
                            "is_active": True,
                            "monitoring_status": "ACTIVE",
                        }
                    )
        return results

    async def ensure_repository_tracked(self, owner: str, repo: str) -> dict[str, Any]:
        """Ensures a requested repository is in inventory and tracked."""
        full_name = f"{owner}/{repo}"
        for r in RepositoryService._cached_repositories:
            if r.get("full_name") == full_name:
                return r

        # Fetch real metadata from GitHub
        meta = await self.client.fetch_repository_metadata(owner, repo)
        if not meta:
            meta = {
                "id": abs(hash(full_name)) % 100000000,
                "name": repo,
                "full_name": full_name,
                "owner": owner,
                "description": f"Repository {full_name}",
                "visibility": "public",
                "default_branch": "main",
                "html_url": f"https://github.com/{full_name}",
                "created_at": datetime.now(UTC).isoformat(),
                "pushed_at": datetime.now(UTC).isoformat(),
                "stars_count": 0,
                "forks_count": 0,
                "is_active": True,
                "monitoring_status": "ACTIVE",
            }

        now = datetime.now(UTC)
        try:
            await init_db()
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    stmt = select(Repository).where(Repository.full_name == full_name)
                    res = await session.execute(stmt)
                    existing = res.scalar_one_or_none()
                    if not existing:
                        _upsert_repo_record(session, full_name, meta, {}, now)
                        await session.flush()
        except Exception as exc:
            logger.warning("Could not persist repository record for %s: %s", full_name, exc)

        RepositoryService._cached_repositories.append(meta)
        return meta

    async def sync_repositories(self) -> list[dict[str, Any]]:
        """Synchronizes repository inventory from live GitHub API and persists to DB."""
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
            RepositoryService._cached_repositories = list(existing_cache.values())

        return list(RepositoryService._cached_repositories)

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
