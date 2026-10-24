"""CLI runner for ingesting GitHub event streams into the GitPulse platform."""

from __future__ import annotations

import argparse
import asyncio

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.ingestion.github_client import GitHubClient
from backend.src.gitpulse.ingestion.kafka_producer import KafkaEventProducer


async def ingest_repository_events(
    repos: list[str],
    max_pages: int = 2,
    publish_to_kafka: bool = True,
) -> dict[str, int]:
    """Fetches events from target repositories and streams them into Kafka topics."""
    client = GitHubClient()
    producer = KafkaEventProducer() if publish_to_kafka else None

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
        published_count = 0

        for event in events:
            if producer:
                # Normalize schema fields
                normalized = {
                    "event_id": event.get("id", f"gen_{published_count}"),
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
                success = producer.publish_event(
                    key=f"{owner}/{repo}",
                    event_data=normalized,
                    validate=True,
                )
                if success:
                    published_count += 1
            else:
                published_count += 1

        summary[f"{owner}/{repo}"] = published_count
        logger.info("Successfully ingested %d events for %s/%s", published_count, owner, repo)

    return summary


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

    args = parser.parse_args()

    target_repos = (
        [args.repo]
        if args.repo
        else [r.strip() for r in settings.GITHUB_TARGET_REPOS.split(",") if r.strip()]
    )

    results = asyncio.run(
        ingest_repository_events(
            repos=target_repos,
            max_pages=args.pages,
            publish_to_kafka=not args.no_kafka,
        )
    )

    print("\n--- GitPulse Ingestion Summary ---")
    for r, count in results.items():
        print(f"  • {r}: {count} events processed & routed")
    print("----------------------------------\n")


if __name__ == "__main__":
    main()
