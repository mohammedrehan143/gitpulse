"""PySpark Batch Aggregator for GitHub Events."""

from typing import Any, Dict, List


class SparkBatchAggregator:
    """Calculates windowed aggregations across repository commits and PRs."""

    def __init__(self, app_name: str = "GitPulse-Batch-Aggregator"):
        self.app_name = app_name

    def compute_daily_velocity(
        self,
        raw_events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Simulates distributed aggregation of daily commit velocity."""
        repo_buckets: Dict[str, Dict[str, Any]] = {}

        for evt in raw_events:
            repo = evt.get("repo_name", "unknown")
            if repo not in repo_buckets:
                repo_buckets[repo] = {
                    "repo_name": repo,
                    "commits": 0,
                    "prs_merged": 0,
                    "unique_actors": set(),
                }

            evt_type = evt.get("event_type")
            actor = evt.get("actor_login")
            if actor:
                repo_buckets[repo]["unique_actors"].add(actor)

            if evt_type == "PushEvent":
                repo_buckets[repo]["commits"] += 1
            elif evt_type == "PullRequestEvent":
                repo_buckets[repo]["prs_merged"] += 1

        return [
            {
                "repo_name": v["repo_name"],
                "total_commits": v["commits"],
                "total_prs_merged": v["prs_merged"],
                "active_contributors_count": len(v["unique_actors"]),
            }
            for v in repo_buckets.values()
        ]
