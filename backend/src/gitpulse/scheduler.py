"""Lightweight Python Ingestion Scheduler for GitPulse.

Automatically runs GitHub repository event ingestion immediately on startup
and repeatedly every N minutes (default: 60) without Apache Airflow, Docker,
or heavy external dependencies.
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.ingestion.runner import run_ingestion_pipeline


class GitPulseScheduler:
    """Asynchronous, lightweight scheduler for recurring GitHub event ingestion."""

    def __init__(
        self,
        interval_minutes: int | None = None,
        max_pages: int = 2,
        notify_discord: bool = False,
    ):
        configured_interval = (
            interval_minutes
            if interval_minutes is not None
            else (
                getattr(settings, "INGESTION_SCHEDULE_INTERVAL_MINUTES", None)
                or getattr(settings, "REPO_DISCOVERY_INTERVAL_MINUTES", 60)
            )
        )
        self.interval_minutes = configured_interval if configured_interval > 0 else 60
        self.max_pages = max_pages
        self.notify_discord = notify_discord

        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._is_running = False
        self._run_count = 0
        self._last_run_time: datetime | None = None
        self._next_run_time: datetime | None = None
        self._last_run_status: str | None = None
        self._last_run_summary: dict[str, int] | None = None

    @property
    def is_running(self) -> bool:
        """Indicates whether the scheduler loop is actively running."""
        return self._is_running

    @property
    def is_job_active(self) -> bool:
        """Indicates whether an ingestion cycle is currently in progress."""
        return self._lock.locked()

    @property
    def run_count(self) -> int:
        """Total number of completed or attempted ingestion runs."""
        return self._run_count

    @property
    def last_run_status(self) -> str | None:
        """Status of the most recent run (SUCCESS, FAILED, or SKIPPED)."""
        return self._last_run_status

    @property
    def next_run_time(self) -> datetime | None:
        """Calculated next execution timestamp."""
        return self._next_run_time

    async def execute_job(self) -> dict[str, Any]:
        """Executes a single ingestion cycle, preventing overlapping runs."""
        if self._lock.locked():
            logger.warning(
                "Ingestion run skipped: previous ingestion cycle is still actively running. "
                "Concurrency lock prevents overlapping execution."
            )
            return {
                "status": "SKIPPED",
                "reason": "Previous job still executing",
                "run_id": self._run_count + 1,
            }

        async with self._lock:
            run_id = self._run_count + 1
            start_time = datetime.now(UTC)
            logger.info("============================================================")
            logger.info(
                "GitPulse Scheduled Ingestion Run #%d STARTING at %s (interval=%dm)",
                run_id,
                start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                self.interval_minutes,
            )
            logger.info(
                "Settings: AUTO_DISCOVER=%s, MAX_PAGES=%d, NOTIFY_DISCORD=%s",
                settings.AUTO_DISCOVER_REPOSITORIES,
                self.max_pages,
                self.notify_discord,
            )
            logger.info("============================================================")

            try:
                summary = await run_ingestion_pipeline(
                    max_pages=self.max_pages,
                    notify_discord=self.notify_discord,
                )
                elapsed = (datetime.now(UTC) - start_time).total_seconds()
                self._run_count = run_id
                self._last_run_time = start_time
                self._last_run_status = "SUCCESS"
                self._last_run_summary = summary

                total_events = sum(summary.values()) if summary else 0
                logger.info(
                    "Ingestion run #%d COMPLETED SUCCESSFULLY in %.2fs. "
                    "Processed %d repositories, %d total events. Summary: %s",
                    run_id,
                    elapsed,
                    len(summary),
                    total_events,
                    summary,
                )
                return {
                    "status": "SUCCESS",
                    "run_id": run_id,
                    "elapsed_seconds": elapsed,
                    "summary": summary,
                }
            except Exception as exc:
                elapsed = (datetime.now(UTC) - start_time).total_seconds()
                self._run_count = run_id
                self._last_run_time = start_time
                self._last_run_status = "FAILED"
                self._last_run_summary = None

                logger.error(
                    "Ingestion run #%d FAILED after %.2fs: %s",
                    run_id,
                    elapsed,
                    exc,
                    exc_info=True,
                )
                # Resilient: do NOT crash scheduler loop on network, DB, or rate limit issues
                return {
                    "status": "FAILED",
                    "run_id": run_id,
                    "elapsed_seconds": elapsed,
                    "error": str(exc),
                }

    async def run_forever(self) -> None:
        """Starts the persistent scheduler loop.

        Executes an ingestion job immediately, then sleeps for the configured
        interval, waking up immediately if shutdown is signaled.
        """
        self._is_running = True
        self._shutdown_event.clear()

        logger.info("============================================================")
        logger.info("  GitPulse Lightweight Ingestion Scheduler Active")
        logger.info(
            "  Interval: Every %d minutes (%d seconds)",
            self.interval_minutes,
            self.interval_minutes * 60,
        )
        logger.info("  Immediate startup execution: ENABLED")
        logger.info("  Platform: %s", sys.platform)
        logger.info("============================================================")

        try:
            while not self._shutdown_event.is_set():
                # Step 1: Execute job (immediate on first pass, repeated thereafter)
                await self.execute_job()

                if self._shutdown_event.is_set():
                    break

                # Step 2: Calculate and log next run time
                now = datetime.now(UTC)
                self._next_run_time = now + timedelta(minutes=self.interval_minutes)
                logger.info(
                    "Next ingestion run scheduled for: %s (in %d minutes)",
                    self._next_run_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    self.interval_minutes,
                )

                # Step 3: Wait for interval or until shutdown event is set
                sleep_seconds = float(self.interval_minutes * 60)
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=sleep_seconds,
                    )
                    # Unblocked before timeout => shutdown requested
                    logger.info("Scheduler shutdown signal detected during sleep window.")
                    break
                except TimeoutError:
                    # Timeout reached => proceed to next scheduled run
                    pass

        except asyncio.CancelledError:
            logger.info("Scheduler task cancelled.")
        finally:
            self._is_running = False
            logger.info("GitPulse Scheduler loop stopped.")

    async def stop(self) -> None:
        """Signals the scheduler to stop gracefully."""
        logger.info("Signaling GitPulse Scheduler to stop...")
        self._shutdown_event.set()
        self._is_running = False


def main() -> None:
    """CLI execution entrypoint for running the scheduler standalone."""
    parser = argparse.ArgumentParser(
        description="GitPulse Lightweight Ingestion Scheduler (Airflow Replacement)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Ingestion interval in minutes (defaults to REPO_DISCOVERY_INTERVAL_MINUTES or 60)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=2,
        help="Max event pages per repository to crawl (default: 2)",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send Discord notification after ingestion cycles",
    )
    args = parser.parse_args()

    scheduler = GitPulseScheduler(
        interval_minutes=args.interval,
        max_pages=args.pages,
        notify_discord=args.notify,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Register OS signals on POSIX systems
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(scheduler.stop()))
            except (NotImplementedError, RuntimeError):
                pass

    try:
        loop.run_until_complete(scheduler.run_forever())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received interrupt signal (Ctrl+C). Initiating graceful shutdown...")
        loop.run_until_complete(scheduler.stop())
    finally:
        # Cancel any pending background tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
        logger.info("GitPulse Scheduler has shut down cleanly.")


def start() -> None:
    """Console script hook."""
    main()


if __name__ == "__main__":
    main()
