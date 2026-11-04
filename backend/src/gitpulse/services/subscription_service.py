"""Repository Subscription & Multi-User Notification Mapping Service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import Repository, RepositorySubscription


async def _find_repository(
    session: Any, repo_github_id: int | None, repo_id: int | None, full_name: str | None
) -> Repository | None:
    if repo_github_id:
        res = await session.execute(select(Repository).where(Repository.github_id == repo_github_id))
        repo = res.scalar_one_or_none()
        if repo:
            return repo
    if repo_id:
        res = await session.execute(select(Repository).where(Repository.id == repo_id))
        repo = res.scalar_one_or_none()
        if repo:
            return repo
    if full_name:
        res = await session.execute(select(Repository).where(Repository.full_name == full_name))
        return res.scalar_one_or_none()
    return None


async def _register_default_owner_sub(session: Any, repo: Repository) -> dict[str, Any] | None:
    owner_name = repo.owner or settings.GITHUB_TARGET_USER or "owner"
    owner_sub = RepositorySubscription(
        repo_id=repo.id,
        repo_github_id=repo.github_id,
        user_id=owner_name,
        webhook_url=settings.DISCORD_WEBHOOK_URL or None,
        event_types=["push", "pull_request", "issues", "all"],
        is_active=True,
        created_at=datetime.now(UTC),
    )
    session.add(owner_sub)
    try:
        await session.commit()
        return {
            "id": owner_sub.id,
            "user_id": owner_sub.user_id,
            "webhook_url": owner_sub.webhook_url or settings.DISCORD_WEBHOOK_URL or "",
            "repo_id": owner_sub.repo_id,
            "repo_github_id": owner_sub.repo_github_id,
            "event_types": ["push", "pull_request", "issues", "all"],
            "is_active": True,
        }
    except Exception as commit_exc:
        logger.debug("Default subscription commit note: %s", commit_exc)
        return None


class SubscriptionService:
    """Manages repository subscribers and determines eligible notification recipients."""

    async def get_subscribers_for_repo(
        self,
        repo_github_id: int | None = None,
        repo_id: int | None = None,
        full_name: str | None = None,
        event_type: str = "push",
    ) -> list[dict[str, Any]]:
        """Returns all active subscribers for a repository, auto-registering defaults if needed."""
        await init_db()
        subscribers: list[dict[str, Any]] = []

        try:
            async with AsyncSessionLocal() as session:
                repo = await _find_repository(session, repo_github_id, repo_id, full_name)
                if repo:
                    sub_stmt = (
                        select(RepositorySubscription)
                        .where(
                            (RepositorySubscription.repo_id == repo.id)
                            | (RepositorySubscription.repo_github_id == repo.github_id)
                        )
                        .where(RepositorySubscription.is_active.is_(True))
                    )
                    sub_res = await session.execute(sub_stmt)
                    existing_subs = list(sub_res.scalars().all())

                    for s in existing_subs:
                        types = s.event_types or ["all"]
                        if event_type in types or "all" in types or "*" in types:
                            subscribers.append(
                                {
                                    "id": s.id,
                                    "user_id": s.user_id,
                                    "webhook_url": s.webhook_url or settings.DISCORD_WEBHOOK_URL or "",
                                    "repo_id": s.repo_id,
                                    "repo_github_id": s.repo_github_id,
                                    "event_types": types,
                                    "is_active": s.is_active,
                                }
                            )

                    # If no subscriptions exist for this repository, create default subscription for the repo owner
                    if not subscribers:
                        default_sub = await _register_default_owner_sub(session, repo)
                        if default_sub:
                            subscribers.append(default_sub)
        except Exception as exc:
            logger.warning("Error fetching subscribers for repo (%s / %s): %s", repo_github_id, full_name, exc)

        # Ensure fallback to default configured webhook if still empty
        if not subscribers and settings.DISCORD_WEBHOOK_URL:
            subscribers.append(
                {
                    "id": 0,
                    "user_id": "default_subscriber",
                    "webhook_url": settings.DISCORD_WEBHOOK_URL,
                    "repo_id": repo_id or 0,
                    "repo_github_id": repo_github_id or 0,
                    "event_types": ["push", "all"],
                    "is_active": True,
                }
            )

        return subscribers

    async def subscribe_user(
        self,
        repo_github_id: int,
        user_id: str,
        repo_id: int | None = None,
        webhook_url: str | None = None,
        event_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Subscribes a user to receive alerts for a repository."""
        await init_db()
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = select(Repository).where(Repository.github_id == repo_github_id)
                res = await session.execute(stmt)
                repo = res.scalar_one_or_none()

                actual_repo_id = repo.id if repo else (repo_id or 0)

                sub_stmt = select(RepositorySubscription).where(
                    RepositorySubscription.repo_github_id == repo_github_id,
                    RepositorySubscription.user_id == user_id,
                )
                sub_res = await session.execute(sub_stmt)
                sub = sub_res.scalar_one_or_none()

                types = event_types or ["push", "all"]
                if sub:
                    sub.is_active = True
                    sub.repo_id = actual_repo_id
                    if webhook_url is not None:
                        sub.webhook_url = webhook_url
                    if event_types is not None:
                        sub.event_types = types
                else:
                    sub = RepositorySubscription(
                        repo_id=actual_repo_id,
                        repo_github_id=repo_github_id,
                        user_id=user_id,
                        webhook_url=webhook_url,
                        event_types=types,
                        is_active=True,
                        created_at=datetime.now(UTC),
                    )
                    session.add(sub)
                await session.flush()
                return {
                    "id": sub.id,
                    "repo_id": sub.repo_id,
                    "repo_github_id": repo_github_id,
                    "user_id": user_id,
                    "webhook_url": sub.webhook_url,
                    "event_types": sub.event_types,
                    "is_active": sub.is_active,
                }

    async def unsubscribe_user(self, repo_github_id: int, user_id: str) -> bool:
        """Deactivates a user's subscription to a repository."""
        await init_db()
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = select(RepositorySubscription).where(
                    RepositorySubscription.repo_github_id == repo_github_id,
                    RepositorySubscription.user_id == user_id,
                )
                res = await session.execute(stmt)
                sub = res.scalar_one_or_none()
                if sub:
                    sub.is_active = False
                    await session.flush()
                    return True
                return False

    async def list_subscribers_for_repo(
        self,
        repo_github_id: int | None = None,
        full_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lists all subscriptions registered for a repository."""
        return await self.get_subscribers_for_repo(
            repo_github_id=repo_github_id, full_name=full_name, event_type="all"
        )


subscription_service = SubscriptionService()
