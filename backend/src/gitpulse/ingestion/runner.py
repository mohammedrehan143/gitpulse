"""CLI runner for ingesting GitHub event streams directly into GitPulse storage."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.ingestion.kafka_producer import KafkaEventProducer
from backend.src.gitpulse.services.notification_service import NotificationService
from backend.src.gitpulse.services.repository_service import RepositoryService
from backend.src.gitpulse.storage.database import AsyncSessionLocal, init_db
from backend.src.gitpulse.storage.models import GitHubEvent, Repository


async def _persist_events_to_db(
    owner: str,
    repo_name: str,
    events: list[dict],
) -> int:
    """Persists raw GitHub events into the relational database (Supabase / SQLite)."""
    full_name = f"{owner}/{repo_name}"
    saved_count = 0
    try:
        await init_db()
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Find or register repository record
                stmt = select(Repository).where(Repository.full_name == full_name)
                res = await session.execute(stmt)
                repo = res.scalar_one_or_none()

                if not repo:
                    repo = Repository(
                        github_id=abs(hash(full_name)) % 10000000,
                        owner=owner,
                        name=repo_name,
                        full_name=full_name,
                        is_active=True,
                        monitoring_status="MONITORED",
                        last_synced_at=datetime.now(UTC),
                    )
                    session.add(repo)
                    await session.flush()
                else:
                    repo.monitoring_status = "MONITORED"
                    repo.last_synced_at = datetime.now(UTC)

                # Fetch existing event_ids to prevent duplicates
                event_ids = [str(e.get("id")) for e in events if e.get("id")]
                existing_event_ids: set[str] = set()
                if event_ids:
                    ev_stmt = select(GitHubEvent.event_id).where(
                        GitHubEvent.event_id.in_(event_ids)
                    )
                    ev_res = await session.execute(ev_stmt)
                    existing_event_ids = set(ev_res.scalars().all())

                for event in events:
                    eid = str(event.get("id", f"gen_{saved_count}"))
                    if eid in existing_event_ids:
                        continue

                    actor = event.get("actor")
                    actor_login = (
                        actor.get("login", "unknown")
                        if isinstance(actor, dict)
                        else str(actor or "unknown")
                    )
                    avatar_url = actor.get("avatar_url") if isinstance(actor, dict) else None

                    created_str = event.get("created_at")
                    created_dt = datetime.now(UTC)
                    if created_str:
                        try:
                            created_dt = datetime.fromisoformat(
                                str(created_str).replace("Z", "+00:00")
                            )
                        except Exception:
                            pass

                    payload = event.get("payload") or {}
                    action = payload.get("action") if isinstance(payload, dict) else None
                    summary_text = f"{event.get('type')}: {action or 'event'} by {actor_login}"

                    db_event = GitHubEvent(
                        event_id=eid,
                        event_type=event.get("type", "UnknownEvent"),
                        repo_id=repo.id,
                        actor_login=actor_login,
                        actor_avatar_url=avatar_url,
                        action=action,
                        payload_summary=summary_text[:500],
                        raw_payload=payload if isinstance(payload, dict) else {},
                        created_at=created_dt,
                    )
                    session.add(db_event)
                    saved_count += 1

                await session.flush()
    except Exception as exc:
        logger.warning(
            "Could not persist events to database for %s: %s (continuing in-memory)",
            full_name,
            exc,
        )
    return saved_count


async def ingest_repository_events(
    repos: list[str],
    max_pages: int = 2,
    publish_to_kafka: bool = False,
    persist_to_db: bool = True,
    notify_discord: bool = False,
) -> dict[str, int]:
    """Fetches events from target repositories, persists to Supabase DB, and streams to clients."""
    client = GitHubClient()
    producer = KafkaEventProducer() if publish_to_kafka else None
    notifier = NotificationService() if notify_discord else None

    rate_budget = client.get_rate_limit_status()
    logger.info(
        "Initial GitHub Rate Limit: %s remaining out of %s",
        rate_budget["remaining"],
        rate_budget["limit"],
    )

    summary: dict[str, int] = {}

    for full_repo in repos:
        parts = full_repo.strip().split("/")
        if len(parts) != 2:
            logger.warning(
                "Skipping invalid repository specifier: '%s' (must be 'owner/repo')", full_repo
            )
            continue
        owner, repo = parts[0], parts[1]
        logger.info("Starting ingestion for %s/%s (max_pages=%d)...", owner, repo, max_pages)

        events = await client.fetch_all_recent_events(owner, repo, max_pages=max_pages)
        processed_count = len(events)

        if persist_to_db and events:
            saved = await _persist_events_to_db(owner, repo, events)
            logger.info("Persisted %d new events to database for %s/%s", saved, owner, repo)

        if producer and events:
            for idx, event in enumerate(events):
                normalized = {
                    "event_id": event.get("id", f"gen_{idx}"),
                    "event_type": event.get("type", "UnknownEvent"),
                    "repo_id": event.get("repo", {}).get("name", f"{owner}/{repo}"),
                    "actor_login": (
                        event.get("actor", {}).get("login", "unknown")
                        if isinstance(event.get("actor"), dict)
                        else str(event.get("actor", "unknown"))
                    ),
                    "created_at": event.get("created_at"),
                    "raw": event,
                }
                producer.publish_event(
                    key=f"{owner}/{repo}",
                    event_data=normalized,
                    validate=True,
                )

        if notifier and events:
            await notifier.send_discord_notification(
                title=f"GitPulse Ingestion: {owner}/{repo}",
                description=f"Ingested {len(events)} events for {owner}/{repo}.",
            )

        summary[f"{owner}/{repo}"] = processed_count
        logger.info("Successfully ingested %d events for %s/%s", processed_count, owner, repo)

    return summary


async def run_ingestion_pipeline(
    target_repos: list[str] | None = None,
    max_pages: int = 2,
    publish_to_kafka: bool = False,
    persist_to_db: bool = True,
    notify_discord: bool = False,
) -> dict[str, int]:
    """Resolves target repositories (via auto-discovery or fallback list) and executes ingestion."""
    if not target_repos:
        repo_service = RepositoryService()
        if settings.AUTO_DISCOVER_REPOSITORIES:
            try:
                await repo_service.sync_repositories()
            except Exception as exc:
                logger.warning(
                    "Repository auto-discovery failed during ingestion pipeline: %s", exc
                )
        target_repos = await repo_service.get_target_repo_names()
        if not target_repos:
            target_repos = [r.strip() for r in settings.GITHUB_TARGET_REPOS.split(",") if r.strip()]

    logger.info(
        "Executing ingestion pipeline over %d target repositories: %s",
        len(target_repos),
        target_repos,
    )
    return await ingest_repository_events(
        repos=target_repos,
        max_pages=max_pages,
        publish_to_kafka=publish_to_kafka,
        persist_to_db=persist_to_db,
        notify_discord=notify_discord,
    )


def main() -> None:
    """CLI execution entrypoint."""
    parser = argparse.ArgumentParser(
        description="GitPulse GitHub Event Ingestion Engine",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Target repository in format 'owner/repo' (defaults to GITHUB_TARGET_REPOS in .env)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=2,
        help="Number of event stream pages to crawl (30 events per page)",
    )
    parser.add_argument(
        "--no-kafka",
        action="store_true",
        help="Disable streaming published events to Kafka buffer",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send Discord notification upon completion",
    )

    args = parser.parse_args()

    results = asyncio.run(
        run_ingestion_pipeline(
            target_repos=[args.repo] if args.repo else None,
            max_pages=args.pages,
            publish_to_kafka=not args.no_kafka,
            persist_to_db=True,
            notify_discord=args.notify,
        )
    )

    print("\n--- GitPulse Ingestion Summary ---")
    for r, count in results.items():
        print(f"  • {r}: {count} events processed & persisted to database")
    print("----------------------------------\n")


if __name__ == "__main__":
    main()
