"""GitHub User Profile Activity Stream Monitor & Universal Discord Dispatcher."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.ingestion.runner import _persist_events_to_db
from backend.src.gitpulse.services.notification_service import NotificationService
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import GitHubEvent


class ProfileMonitorService:
    """Continuously monitors an entire GitHub profile across all user repos.

    Detects any push, pull request, issue, commit, branch create, or delete
    and delivers an automated real-time alert to Discord.
    """

    def __init__(
        self,
        username: str | None = None,
        client: GitHubClient | None = None,
        notifier: NotificationService | None = None,
        interval_seconds: int | None = None,
    ):
        self.username = username or settings.GITHUB_TARGET_USER or "mohammedrehan143"
        self.client = client or GitHubClient()
        self.notifier = notifier or NotificationService()
        self.interval_seconds = interval_seconds or settings.PROFILE_MONITOR_INTERVAL_SECONDS or 20
        self.seen_event_ids: set[str] = set()
        self._is_primed = False
        self._running = False
        self._task: asyncio.Task | None = None

    async def _prime_seen_ids(self) -> None:
        """Loads historical event IDs to prevent duplicate alerts on initial startup."""
        if self._is_primed:
            return

        try:
            await init_db()
            async with AsyncSessionLocal() as session:
                stmt = select(GitHubEvent.event_id).limit(1000)
                res = await session.execute(stmt)
                for eid in res.scalars().all():
                    self.seen_event_ids.add(str(eid))
        except Exception as exc:
            logger.debug("Database event pre-prime note: %s", exc)

        # Also fetch current user profile events and mark them seen if empty
        if not self.seen_event_ids:
            try:
                initial_events = await self.client.fetch_user_events(
                    self.username, page=1, per_page=30
                )
                for ev in initial_events:
                    eid = str(ev.get("id", ""))
                    if eid:
                        self.seen_event_ids.add(eid)
                logger.info(
                    "Primed profile monitor for @%s with %d existing events.",
                    self.username,
                    len(self.seen_event_ids),
                )
            except Exception as exc:
                logger.warning("Error fetching initial user events for priming: %s", exc)

        self._is_primed = True

    async def poll_and_notify(self) -> int:
        """Polls the user's GitHub event feed and dispatches alerts for newly detected activities."""
        await self._prime_seen_ids()

        events = await self.client.fetch_user_events(self.username, page=1, per_page=30)
        if not events:
            return 0

        # Filter events that haven't been processed yet
        new_events = [e for e in events if str(e.get("id", "")) not in self.seen_event_ids]
        if not new_events:
            return 0

        # Process in chronological order (oldest to newest)
        new_events.reverse()
        dispatched_count = 0

        for event in new_events:
            eid = str(event.get("id", ""))
            self.seen_event_ids.add(eid)

            repo_meta = event.get("repo", {})
            repo_name = (
                repo_meta.get("name") if isinstance(repo_meta, dict) else str(repo_meta or "")
            )

            # 1. Dispatch Discord notification
            try:
                alert_success = await self.notifier.notify_github_event(event)
                if alert_success:
                    dispatched_count += 1
            except Exception as exc:
                logger.error("Failed to dispatch Discord alert for event %s: %s", eid, exc)

            # 2. Persist event to database
            if "/" in repo_name:
                parts = repo_name.split("/", 1)
                try:
                    await _persist_events_to_db(parts[0], parts[1], [event])
                except Exception as exc:
                    logger.debug("Event persistence note for %s: %s", repo_name, exc)

        logger.info(
            "Profile monitor for @%s processed %d new events (dispatched %d alerts).",
            self.username,
            len(new_events),
            dispatched_count,
        )
        return dispatched_count

    async def run_monitor_loop(self) -> None:
        """Background loop continuously polling the user profile for new events."""
        logger.info(
            "Starting GitPulse Universal Profile Monitor for @%s (interval: %ds)...",
            self.username,
            self.interval_seconds,
        )
        self._running = True
        while self._running:
            try:
                await self.poll_and_notify()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in profile monitor loop for @%s: %s", self.username, exc)

            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    def start(self) -> asyncio.Task:
        """Launches the monitor loop as an asyncio background task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run_monitor_loop())
        return self._task

    def stop(self) -> None:
        """Stops the background monitor loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()


# Singleton instance
profile_monitor = ProfileMonitorService()
