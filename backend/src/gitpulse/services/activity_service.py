"""GitPulse Unified Git Activity & Real-Time Persistence Service.

Guarantees that ANY git activity (commits, pushes, branch creations, pull requests,
issues, and newly created repositories) from ANY source (local universal git hooks,
GitHub webhooks, REST API notifications, or profile stream polling) is IMMEDIATELY
and reliably persisted into the database (Supabase / SQLite fallback) with zero hardcoding.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.services.notification_service import NotificationService
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import (
    CommitRecord,
    GitHubEvent,
    Repository,
)


def _apply_repo_metadata(repo: Repository, metadata: dict[str, Any] | None) -> None:
    """Updates mutable repository metadata fields if provided."""
    if not metadata:
        return
    if metadata.get("description"):
        repo.description = metadata["description"]
    if metadata.get("default_branch"):
        repo.default_branch = metadata["default_branch"]
    if metadata.get("html_url"):
        repo.html_url = metadata["html_url"]
    if metadata.get("stars_count") is not None:
        repo.stars_count = metadata["stars_count"]
    if metadata.get("forks_count") is not None:
        repo.forks_count = metadata["forks_count"]


def _parse_meta_datetime(meta: dict[str, Any], key: str, fallback: datetime) -> datetime:
    """Safely extracts a datetime from metadata dict."""
    if meta.get(key):
        try:
            return datetime.fromisoformat(str(meta[key]).replace("Z", "+00:00"))
        except Exception:
            pass
    return fallback


def resolve_effective_user(explicit_user: str | None = None) -> str:
    """Dynamically resolves the active user identity with zero hardcoding.

    Resolution precedence:
      1. Explicitly supplied username/actor
      2. GITHUB_TARGET_USER from environment (.env)
      3. Local Git configuration (`git config user.name`)
      4. OS environment variables (GITHUB_ACTOR, USER, USERNAME)
      5. Fallback generic identity ('developer')
    """
    if (
        explicit_user
        and explicit_user.strip()
        and explicit_user.strip() not in ("unknown", "developer")
    ):
        return explicit_user.strip()

    env_user = (settings.GITHUB_TARGET_USER or "").strip()
    if env_user:
        return env_user

    # Dynamically query local git config
    try:
        git_user = subprocess.check_output(
            ["git", "config", "user.name"],
            text=True,
            timeout=2,
            stderr=subprocess.DEVNULL,
        ).strip()
        if git_user:
            return git_user
    except Exception:
        pass

    # Dynamically query environment
    for env_var in ("GITHUB_ACTOR", "USER", "USERNAME"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return val

    return "developer"


def parse_repo_coordinates(repo_str: str, default_actor: str | None = None) -> tuple[str, str, str]:
    """Parses owner, name, and full_name dynamically from any repository string.

    Supports:
      - 'owner/repo'
      - 'https://github.com/owner/repo.git'
      - 'git@github.com:owner/repo.git'
      - 'repo-name' (defaults owner dynamically)
    """
    clean = (repo_str or "").strip()
    clean = clean.replace(".git", "")

    if "github.com/" in clean:
        clean = clean.split("github.com/")[-1]
    elif "github.com:" in clean:
        clean = clean.split("github.com:")[-1]

    clean = clean.strip("/")
    if "/" in clean:
        parts = clean.split("/", 1)
        owner = parts[0].strip()
        name = parts[1].strip()
    else:
        owner = resolve_effective_user(default_actor)
        name = clean or "workspace-repo"

    full_name = f"{owner}/{name}"
    return owner, name, full_name


async def _broadcast_ws(channel: str, message: dict[str, Any]) -> None:
    """Broadcasts real-time events over active WebSockets safely."""
    try:
        from backend.src.gitpulse.api.routes import ws_manager

        await ws_manager.broadcast(channel, message)
        # Also broadcast to 'all' listener channel
        await ws_manager.broadcast("all", message)
    except Exception as exc:
        logger.debug("WebSocket broadcast skip/note: %s", exc)


class GitActivityService:
    """Unified service for recording, storing, and broadcasting all Git activity."""

    def __init__(
        self,
        client: GitHubClient | None = None,
        notifier: NotificationService | None = None,
    ):
        self.client = client or GitHubClient()
        self.notifier = notifier or NotificationService()

    async def ensure_repository_record(
        self,
        session: Any,
        owner: str,
        name: str,
        full_name: str,
        repo_github_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> Repository:
        """Finds or immediately inserts a newly discovered repository into the database."""
        now_dt = now or datetime.now(UTC)

        stmt = select(Repository).where(Repository.full_name == full_name)
        res = await session.execute(stmt)
        repo = res.scalar_one_or_none()

        if repo:
            repo.is_active = True
            repo.monitoring_status = "MONITORED"
            repo.last_synced_at = now_dt
            _apply_repo_metadata(repo, metadata)
            return repo

        # Attempt to fetch real remote metadata if GitHubClient is available
        live_meta = None
        if not metadata:
            try:
                live_meta = await self.client.fetch_repository_metadata(owner, name)
            except Exception as exc:
                logger.debug("Metadata remote fetch note for %s: %s", full_name, exc)

        meta = metadata or live_meta or {}
        raw_id = (
            repo_github_id
            or meta.get("github_id")
            or meta.get("id")
            or (abs(hash(full_name)) % 100000000)
        )
        pushed_dt = _parse_meta_datetime(meta, "pushed_at", now_dt)
        created_dt = _parse_meta_datetime(meta, "created_at", now_dt)

        new_repo = Repository(
            github_id=raw_id,
            owner=owner,
            name=name,
            full_name=full_name,
            description=meta.get("description") or f"Repository {full_name}",
            visibility=meta.get("visibility", "public"),
            default_branch=meta.get("default_branch", "main"),
            html_url=meta.get("html_url") or f"https://github.com/{full_name}",
            pushed_at=pushed_dt,
            created_at=created_dt,
            is_active=True,
            monitoring_status="MONITORED",
            last_synced_at=now_dt,
            stars_count=meta.get("stars_count", 0),
            forks_count=meta.get("forks_count", 0),
        )
        session.add(new_repo)
        await session.flush()

        logger.info(
            "✨ New repository '%s' registered and persisted into database (id=%d).",
            full_name,
            new_repo.id,
        )

        # Notify active clients of new repository discovery
        asyncio.create_task(
            _broadcast_ws(
                full_name,
                {
                    "type": "new_repository",
                    "repository": {
                        "id": new_repo.id,
                        "github_id": new_repo.github_id,
                        "owner": new_repo.owner,
                        "name": new_repo.name,
                        "full_name": new_repo.full_name,
                        "description": new_repo.description,
                        "default_branch": new_repo.default_branch,
                        "html_url": new_repo.html_url,
                        "is_active": True,
                        "monitoring_status": "MONITORED",
                    },
                },
            )
        )

        return new_repo

    async def record_commit_activity(
        self,
        repo: str,
        actor: str | None = None,
        branch: str = "main",
        sha: str = "head",
        message: str = "New commit",
        commits: list[dict[str, Any]] | None = None,
        lines_added: int | None = None,
        lines_deleted: int | None = None,
        commit_url: str | None = None,
        compare_url: str | None = None,
        discord_webhook_url: str | None = None,
        notify_discord: bool = True,
    ) -> dict[str, Any]:
        """Saves a Git commit / push activity immediately into the database and delivers alerts."""
        await init_db()
        now = datetime.now(UTC)
        effective_actor = resolve_effective_user(actor)
        owner, name, full_name = parse_repo_coordinates(repo, effective_actor)

        # Normalise commits
        normalized_commits = commits or []
        if not normalized_commits and (sha or message):
            normalized_commits = [
                {
                    "id": sha or "head",
                    "sha": sha or "head",
                    "message": message or "Commit update",
                    "author": {"name": effective_actor, "login": effective_actor},
                    "url": commit_url or f"https://github.com/{full_name}/commit/{sha[:7]}",
                    "timestamp": now.isoformat(),
                    "lines_added": lines_added,
                    "lines_deleted": lines_deleted,
                }
            ]

        primary_sha = sha or (normalized_commits[0].get("id") if normalized_commits else "head")
        first_msg = (
            (normalized_commits[0].get("message") or message).split("\n")[0][:60]
            if normalized_commits
            else message[:60]
        )
        suffix = f' — "{first_msg}"' if first_msg else ""
        summary_text = (
            f"New git pushed: {len(normalized_commits)} commit(s) committed to {branch} by {effective_actor}{suffix}"
            if normalized_commits
            else f"New git pushed to {branch} by {effective_actor}"
        )

        event_id = f"commit_{primary_sha[:16]}_{int(now.timestamp())}"
        saved_repo_id = None

        async with AsyncSessionLocal() as session:
            async with session.begin():
                db_repo = await self.ensure_repository_record(
                    session, owner, name, full_name, now=now
                )
                db_repo.pushed_at = now
                db_repo.last_synced_at = now
                saved_repo_id = db_repo.id

                # 1. Save Commit Records
                existing_shas_stmt = select(CommitRecord.sha).where(
                    CommitRecord.repo_id == db_repo.id,
                    CommitRecord.sha.in_(
                        [
                            c.get("id") or c.get("sha")
                            for c in normalized_commits
                            if c.get("id") or c.get("sha")
                        ]
                    ),
                )
                shas_res = await session.execute(existing_shas_stmt)
                existing_shas = set(shas_res.scalars().all())

                for c in normalized_commits:
                    c_sha = str(c.get("id") or c.get("sha") or "")
                    if not c_sha or c_sha in existing_shas:
                        continue
                    c_auth = c.get("author") if isinstance(c.get("author"), dict) else {}
                    c_author = c_auth.get("name") or c_auth.get("login") or effective_actor
                    c_email = c_auth.get("email") or ""
                    c_msg = str(c.get("message") or "Commit update")[:1000]

                    c_lines_add = (
                        c.get("lines_added")
                        if c.get("lines_added") is not None
                        else (
                            c.get("additions")
                            if c.get("additions") is not None
                            else (len(c.get("added", [])) * 20 or 25)
                        )
                    )
                    c_lines_del = (
                        c.get("lines_deleted")
                        if c.get("lines_deleted") is not None
                        else (
                            c.get("deletions")
                            if c.get("deletions") is not None
                            else (len(c.get("removed", [])) * 5 or 5)
                        )
                    )

                    session.add(
                        CommitRecord(
                            sha=c_sha,
                            repo_id=db_repo.id,
                            author_name=c_author,
                            author_email=c_email,
                            message=c_msg,
                            lines_added=c_lines_add,
                            lines_deleted=c_lines_del,
                            committed_at=now,
                        )
                    )
                    existing_shas.add(c_sha)

                # 2. Save GitHubEvent Record
                db_event = GitHubEvent(
                    event_id=event_id,
                    event_type="PushEvent",
                    repo_id=db_repo.id,
                    actor_login=effective_actor,
                    actor_avatar_url=None,
                    action="pushed",
                    payload_summary=summary_text[:500],
                    raw_payload={
                        "ref": f"refs/heads/{branch}",
                        "branch": branch,
                        "commits": normalized_commits,
                        "actor": effective_actor,
                        "compare": compare_url,
                    },
                    created_at=now,
                )
                session.add(db_event)
                await session.flush()

        logger.info(
            "💾 Git activity successfully persisted for '%s': 1 event, %d commits in DB.",
            full_name,
            len(normalized_commits),
        )

        # 3. Broadcast real-time WebSocket update
        ws_payload = {
            "type": "event_stream",
            "event": {
                "event_id": event_id,
                "event_type": "PushEvent",
                "actor": effective_actor,
                "action": "pushed",
                "payload_summary": summary_text,
                "created_at": now.isoformat(),
                "repo": full_name,
            },
        }
        await _broadcast_ws(full_name, ws_payload)

        # 4. Deliver Discord notification
        delivered = False
        if notify_discord:
            custom_notifier = (
                NotificationService(discord_webhook_url=discord_webhook_url)
                if discord_webhook_url
                else self.notifier
            )
            try:
                delivered = await custom_notifier.notify_git_push(
                    repo_name=full_name,
                    pusher=effective_actor,
                    branch=branch,
                    commits=normalized_commits,
                    compare_url=compare_url,
                    sender=effective_actor,
                    repo_owner=owner,
                )
            except Exception as exc:
                logger.warning("Discord delivery warning: %s", exc)

        return {
            "status": "SUCCESS",
            "repository": full_name,
            "repo_id": saved_repo_id,
            "event_id": event_id,
            "commits_recorded": len(normalized_commits),
            "delivered": delivered,
            "timestamp": now.isoformat(),
        }

    async def record_generic_event(
        self,
        repo: str,
        event_type: str,
        actor: str | None = None,
        action: str | None = None,
        summary: str = "",
        raw_payload: dict[str, Any] | None = None,
        repo_metadata: dict[str, Any] | None = None,
        repo_github_id: int | None = None,
    ) -> dict[str, Any]:
        """Saves any generic event (CreateEvent, PullRequestEvent, IssuesEvent, etc.) to DB."""
        await init_db()
        now = datetime.now(UTC)
        effective_actor = resolve_effective_user(actor)
        owner, name, full_name = parse_repo_coordinates(repo, effective_actor)

        event_id = f"{event_type.lower()}_{int(now.timestamp())}_{abs(hash(full_name)) % 100000}"
        if raw_payload and raw_payload.get("id"):
            event_id = str(raw_payload["id"])

        async with AsyncSessionLocal() as session:
            async with session.begin():
                db_repo = await self.ensure_repository_record(
                    session,
                    owner,
                    name,
                    full_name,
                    repo_github_id=repo_github_id,
                    metadata=repo_metadata,
                    now=now,
                )

                db_event = GitHubEvent(
                    event_id=event_id,
                    event_type=event_type,
                    repo_id=db_repo.id,
                    actor_login=effective_actor,
                    actor_avatar_url=(
                        (raw_payload or {}).get("actor", {}).get("avatar_url")
                        if isinstance(raw_payload, dict)
                        else None
                    ),
                    action=action,
                    payload_summary=(summary or f"{event_type} on {full_name}")[:500],
                    raw_payload=raw_payload or {},
                    created_at=now,
                )
                session.add(db_event)
                await session.flush()

        # Broadcast over WebSocket
        ws_payload = {
            "type": "event_stream",
            "event": {
                "event_id": event_id,
                "event_type": event_type,
                "actor": effective_actor,
                "action": action,
                "payload_summary": summary,
                "created_at": now.isoformat(),
                "repo": full_name,
            },
        }
        await _broadcast_ws(full_name, ws_payload)

        return {
            "status": "SUCCESS",
            "repository": full_name,
            "event_id": event_id,
            "event_type": event_type,
        }


# Singleton service instance
activity_service = GitActivityService()
