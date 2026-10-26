"""Autonomous Keep-Alive & Self-Warming Pulse Service for GitPulse Platform.

Prevents free-tier cloud containers (such as Render) from entering dormant sleep
after 15 minutes of inactivity by issuing an automated network ping every 5 minutes
and keeping the PostgreSQL/SQLite database connection pool active.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, select

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.storage.database import AsyncSessionLocal
from backend.src.gitpulse.storage.models import GitHubEvent, Repository


class KeepAliveService:
    """Manages periodic self-ping requests and database connectivity pulses."""

    _instance: KeepAliveService | None = None

    def __init__(self) -> None:
        self.start_time = time.monotonic()
        self.pulse_count: int = 0
        self.last_pulse_at: datetime | None = None
        self._task: asyncio.Task[None] | None = None
        self._running: bool = False

    @classmethod
    def get_instance(cls) -> KeepAliveService:
        """Singleton accessor for KeepAliveService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def uptime_seconds(self) -> float:
        """Total uptime in seconds since service initialization."""
        return round(time.monotonic() - self.start_time, 2)

    def resolve_target_url(self) -> str | None:
        """Resolves the public external URL of this service to self-ping."""
        url = (
            settings.RENDER_EXTERNAL_URL
            or settings.BACKEND_PUBLIC_URL
            or os.environ.get("RENDER_EXTERNAL_URL")
            or os.environ.get("BACKEND_URL")
            or os.environ.get("RENDER_SERVICE_URL")
        )
        if url:
            url = url.strip().rstrip("/")
            if not url.startswith("http://") and not url.startswith("https://"):
                url = f"https://{url}"
            return url
        return None

    async def execute_pulse_check(
        self, source: str = "internal", trigger_sync: bool = False
    ) -> dict[str, Any]:
        """Touches the database, verifies data freshness, and updates pulse state."""
        self.pulse_count += 1
        now = datetime.now(UTC)
        self.last_pulse_at = now

        db_status = "CONNECTED"
        repos_count = 0
        events_count = 0
        last_synced_str: str | None = None

        try:
            async with AsyncSessionLocal() as session:
                # Query repository count to keep SQL pool and database awake
                repo_res = await session.execute(select(func.count(Repository.id)))
                repos_count = repo_res.scalar() or 0

                # Query latest event count
                event_res = await session.execute(select(func.count(GitHubEvent.id)))
                events_count = event_res.scalar() or 0

                # Query last sync time
                last_repo = await session.execute(
                    select(Repository.last_synced_at)
                    .order_by(Repository.last_synced_at.desc())
                    .limit(1)
                )
                last_synced_dt = last_repo.scalar()
                if last_synced_dt:
                    last_synced_str = last_synced_dt.isoformat()
        except Exception as exc:
            db_status = f"WARNING: {exc}"
            logger.warning("[KeepAlive] Database pulse encountered issue: %s", exc)

        # Trigger on-demand sync if explicitly requested or if database has 0 repositories
        if trigger_sync or (repos_count == 0 and settings.AUTO_DISCOVER_REPOSITORIES):
            try:
                from backend.src.gitpulse.services.repository_service import RepositoryService

                repo_service = RepositoryService()
                logger.info("[KeepAlive] Triggering database sync pulse...")
                synced = await repo_service.sync_repositories()
                repos_count = len(synced)
                last_synced_str = datetime.now(UTC).isoformat()
            except Exception as sync_exc:
                logger.warning("[KeepAlive] Background database sync pulse failed: %s", sync_exc)

        logger.info(
            "[KeepAlive #%d] Pulse completed via '%s' (DB: %s, Repos: %d, Events: %d, Uptime: %.1fs)",
            self.pulse_count,
            source,
            db_status,
            repos_count,
            events_count,
            self.uptime_seconds,
        )

        return {
            "status": "ALIVE",
            "timestamp": now.isoformat(),
            "database": db_status,
            "repositories_count": repos_count,
            "events_count": events_count,
            "last_synced_at": last_synced_str,
            "uptime_seconds": self.uptime_seconds,
            "keep_alive_pulse": True,
            "source": source,
            "message": "GitPulse server and database kept awake successfully.",
        }

    async def _ping_loop(self) -> None:
        """Internal worker loop that sends a keep-alive pulse every 5 minutes."""
        interval = max(30, settings.KEEP_ALIVE_INTERVAL_SECONDS)
        logger.info(
            "[KeepAlive] Self-warming pulse worker initialized. Pulse interval: %d seconds (5 mins).",
            interval,
        )

        while self._running:
            try:
                await asyncio.sleep(interval)
                if not self._running:
                    break

                target_url = self.resolve_target_url()
                if target_url:
                    ping_endpoint = f"{target_url}/api/v1/keepalive?source=autonomous_pinger"
                    try:
                        async with httpx.AsyncClient(timeout=20.0) as client:
                            resp = await client.get(ping_endpoint)
                            logger.info(
                                "[KeepAlive] Outbound self-ping sent to %s -> Status: %d",
                                ping_endpoint,
                                resp.status_code,
                            )
                    except Exception as http_err:
                        logger.warning(
                            "[KeepAlive] Outbound self-ping to %s failed (%s), running fallback local pulse.",
                            ping_endpoint,
                            http_err,
                        )
                        await self.execute_pulse_check(source="local_fallback_pulse")
                else:
                    # When no external URL is configured (e.g. local dev), pulse the DB directly
                    await self.execute_pulse_check(source="in_process_worker")

            except asyncio.CancelledError:
                logger.info("[KeepAlive] Worker loop cancellation received.")
                break
            except Exception as loop_exc:
                logger.error("[KeepAlive] Error in self-warming loop: %s", loop_exc)
                await asyncio.sleep(10)

    def start(self) -> asyncio.Task[None] | None:
        """Starts the autonomous background keep-alive loop."""
        if not settings.ENABLE_KEEP_ALIVE:
            logger.info("[KeepAlive] Keep-alive worker disabled by configuration.")
            return None

        if self._running and self._task and not self._task.done():
            return self._task

        self._running = True
        self._task = asyncio.create_task(self._ping_loop())
        return self._task

    def stop(self) -> None:
        """Stops the autonomous keep-alive background worker."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()


keep_alive_service = KeepAliveService.get_instance()
