"""Notification and Webhook Dispatch Service (Discord, etc.)."""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import UTC, datetime
from typing import Any

import httpx

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger


class NotificationService:
    """Dispatches event alerts and metrics digests to external channels."""

    def __init__(self, discord_webhook_url: str | None = None):
        self.webhook_url = (
            discord_webhook_url
            if discord_webhook_url is not None
            else (settings.DISCORD_WEBHOOK_URL or os.environ.get("DISCORD_WEBHOOK_URL") or "")
        )

    async def send_discord_notification(
        self,
        title: str,
        description: str,
        color: int = 0x38BDF8,  # GitPulse Cyan
        fields: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Sends rich embed notification to configured Discord webhook."""
        if not self.webhook_url:
            logger.debug("Discord webhook URL not configured. Skipping alert.")
            return False

        payload = {
            "username": "GitPulse Engine",
            "avatar_url": "https://avatars.githubusercontent.com/u/9919?s=200&v=4",
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": color,
                    "fields": fields or [],
                    "footer": {
                        "text": f"GitPulse Analytics Platform • {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    },
                }
            ],
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(self.webhook_url, json=payload)
                if resp.status_code in (200, 204):
                    logger.info(
                        "Discord notification sent successfully: %s",
                        title.encode("ascii", "ignore").decode(),
                    )
                    return True
                else:
                    logger.warning(
                        "Discord webhook returned status %d: %s",
                        resp.status_code,
                        resp.text,
                    )
                    return False
            except Exception as exc:
                logger.error("Failed to deliver Discord notification: %s", exc)
                return False

    async def notify_git_push(
        self,
        repo_name: str,
        pusher: str,
        branch: str,
        commits: list[dict[str, Any]],
        compare_url: str | None = None,
    ) -> bool:
        """Sends an automated rich Discord alert when a new git push is received."""
        if not self.webhook_url:
            logger.debug("Discord webhook URL not configured. Skipping git push alert.")
            return False

        commit_count = len(commits)
        title = f"🚀 New Git Push: {repo_name}"
        description = f"**{pusher}** pushed **{commit_count} commit(s)** to branch `{branch}`."

        fields: list[dict[str, Any]] = [
            {
                "name": "📦 Repository",
                "value": f"[{repo_name}](https://github.com/{repo_name})",
                "inline": True,
            },
            {"name": "🌿 Branch", "value": f"`{branch}`", "inline": True},
            {"name": "👤 Pusher", "value": f"**{pusher}**", "inline": True},
        ]

        if commits:
            commit_lines = []
            for c in commits[:5]:
                sha_short = str(c.get("id") or c.get("sha") or "")[:7]
                msg = str(c.get("message") or "Commit update").split("\n")[0][:60]
                url = c.get("url") or f"https://github.com/{repo_name}/commit/{sha_short}"
                commit_lines.append(f"• [`{sha_short}`]({url}) {msg}")
            if len(commits) > 5:
                commit_lines.append(f"...and {len(commits) - 5} more commit(s)")
            fields.append(
                {"name": "📝 Recent Commits", "value": "\n".join(commit_lines), "inline": False}
            )

        if compare_url:
            fields.append(
                {
                    "name": "🔍 Compare Changes",
                    "value": f"[View Full Diff]({compare_url})",
                    "inline": False,
                }
            )

        return await self.send_discord_notification(
            title=title,
            description=description,
            color=0x10B981,  # Emerald Green for push success
            fields=fields,
        )

    async def notify_github_event(self, event: dict[str, Any]) -> bool:
        """Universal dispatcher that sends Discord notifications for ANY GitHub event."""
        if not self.webhook_url:
            return False

        ev_type = event.get("type", "UnknownEvent")
        repo_data = event.get("repo", {})
        repo_name = (
            repo_data.get("name") if isinstance(repo_data, dict) else str(repo_data or "general")
        )
        actor_data = event.get("actor", {})
        actor = (
            actor_data.get("login")
            if isinstance(actor_data, dict)
            else str(actor_data or "developer")
        )
        payload = event.get("payload", {}) or {}

        if ev_type == "PushEvent":
            commits = payload.get("commits") or []
            ref = payload.get("ref") or "refs/heads/main"
            branch = ref.replace("refs/heads/", "")
            head = payload.get("head") or ""
            compare_url = f"https://github.com/{repo_name}/commit/{head}" if head else None
            return await self.notify_git_push(
                repo_name=repo_name,
                pusher=actor,
                branch=branch,
                commits=commits,
                compare_url=compare_url,
            )

        if ev_type == "PullRequestEvent":
            action = payload.get("action") or "updated"
            pr = payload.get("pull_request") or {}
            pr_num = pr.get("number") or payload.get("number") or ""
            pr_title = pr.get("title") or "Pull Request"
            pr_url = pr.get("html_url") or f"https://github.com/{repo_name}/pull/{pr_num}"
            return await self.send_discord_notification(
                title=f"🔀 Pull Request {action.upper()}: {repo_name} #{pr_num}",
                description=f"**{actor}** {action} pull request: **[{pr_title}]({pr_url})**",
                color=0x8B5CF6,
                fields=[
                    {
                        "name": "📦 Repository",
                        "value": f"[{repo_name}](https://github.com/{repo_name})",
                        "inline": True,
                    },
                    {"name": "👤 Author", "value": f"**{actor}**", "inline": True},
                    {
                        "name": "🔗 PR Link",
                        "value": f"[Open PR #{pr_num}]({pr_url})",
                        "inline": True,
                    },
                ],
            )

        if ev_type == "IssuesEvent":
            action = payload.get("action") or "updated"
            issue = payload.get("issue") or {}
            num = issue.get("number") or payload.get("number") or ""
            title_i = issue.get("title") or "Issue"
            url_i = issue.get("html_url") or f"https://github.com/{repo_name}/issues/{num}"
            return await self.send_discord_notification(
                title=f"⚠️ Issue {action.upper()}: {repo_name} #{num}",
                description=f"**{actor}** {action} issue: **[{title_i}]({url_i})**",
                color=0xF59E0B,
                fields=[
                    {
                        "name": "📦 Repository",
                        "value": f"[{repo_name}](https://github.com/{repo_name})",
                        "inline": True,
                    },
                    {"name": "👤 Author", "value": f"**{actor}**", "inline": True},
                    {
                        "name": "🔗 Issue Link",
                        "value": f"[Open Issue #{num}]({url_i})",
                        "inline": True,
                    },
                ],
            )

        if ev_type == "CreateEvent":
            ref_type = payload.get("ref_type", "branch")
            ref_name = payload.get("ref") or "new"
            return await self.send_discord_notification(
                title=f"🌿 New {ref_type.capitalize()} Created: {repo_name}",
                description=f"**{actor}** created {ref_type} `{ref_name}` in **[{repo_name}](https://github.com/{repo_name})**.",
                color=0x38BDF8,
                fields=[
                    {
                        "name": "📦 Repository",
                        "value": f"[{repo_name}](https://github.com/{repo_name})",
                        "inline": True,
                    },
                    {
                        "name": f"🌿 {ref_type.capitalize()}",
                        "value": f"`{ref_name}`",
                        "inline": True,
                    },
                    {"name": "👤 Created By", "value": f"**{actor}**", "inline": True},
                ],
            )

        if ev_type == "DeleteEvent":
            ref_type = payload.get("ref_type", "branch")
            ref_name = payload.get("ref") or ""
            return await self.send_discord_notification(
                title=f"🗑️ {ref_type.capitalize()} Deleted: {repo_name}",
                description=f"**{actor}** deleted {ref_type} `{ref_name}` in **[{repo_name}](https://github.com/{repo_name})**.",
                color=0xEF4444,
                fields=[
                    {
                        "name": "📦 Repository",
                        "value": f"[{repo_name}](https://github.com/{repo_name})",
                        "inline": True,
                    },
                    {"name": "👤 Deleted By", "value": f"**{actor}**", "inline": True},
                ],
            )

        # Default fallback for other events (WatchEvent, ForkEvent, ReleaseEvent, etc.)
        return await self.send_discord_notification(
            title=f"⚡ GitHub Activity: {repo_name} ({ev_type})",
            description=f"**{actor}** triggered `{ev_type}` on **[{repo_name}](https://github.com/{repo_name})**.",
            color=0x6366F1,
            fields=[
                {
                    "name": "📦 Repository",
                    "value": f"[{repo_name}](https://github.com/{repo_name})",
                    "inline": True,
                },
                {"name": "👤 Actor", "value": f"**{actor}**", "inline": True},
            ],
        )


def main():
    """CLI utility to dispatch a test or automated Git push alert to Discord."""
    parser = argparse.ArgumentParser(description="GitPulse Discord Notification CLI")
    parser.add_argument("--webhook-url", default=None, help="Discord Webhook URL override")
    parser.add_argument("--repo", default="gitpulse", help="Repository full name")
    parser.add_argument("--pusher", default="developer", help="Pusher username")
    parser.add_argument("--branch", default="main", help="Target branch")
    parser.add_argument(
        "--message", default="Automated Git push notification from GitPulse", help="Commit message"
    )
    parser.add_argument("--sha", default="head", help="Commit SHA hash")
    args = parser.parse_args()

    notifier = NotificationService(discord_webhook_url=args.webhook_url)
    commits = [{"id": args.sha, "message": args.message}]

    success = asyncio.run(
        notifier.notify_git_push(
            repo_name=args.repo,
            pusher=args.pusher,
            branch=args.branch,
            commits=commits,
        )
    )
    if success:
        print("[GitPulse] Discord notification delivered successfully.")
    else:
        print("[GitPulse] Discord notification skipped or failed (check DISCORD_WEBHOOK_URL).")


if __name__ == "__main__":
    main()
