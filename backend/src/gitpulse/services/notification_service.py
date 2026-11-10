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


def _format_commit_lines(
    commits: list[dict[str, Any]], repo_name: str, actor_display: str
) -> list[str]:
    lines = []
    for c in commits[:5]:
        sha_short = str(c.get("id") or c.get("sha") or "")[:7]
        msg = str(c.get("message") or "Commit update").split("\n")[0][:60]
        url = c.get("url") or f"https://github.com/{repo_name}/commit/{sha_short}"
        c_auth = c.get("author", {}) if isinstance(c.get("author"), dict) else {}
        c_author = c_auth.get("name") or c_auth.get("username")
        auth_tag = f" by **{c_author}**" if c_author and c_author != actor_display else ""
        lines.append(f"• [`{sha_short}`]({url}){auth_tag}: {msg}")
    if len(commits) > 5:
        lines.append(f"...and {len(commits) - 5} more commit(s)")
    return lines


def _build_git_push_fields(
    repo_name: str,
    pusher: str,
    branch: str,
    commits: list[dict[str, Any]],
    compare_url: str | None,
    sender: str | None,
    repo_owner: str | None,
) -> tuple[str, str, list[dict[str, Any]]]:
    commit_count = len(commits)
    title = f"🚀 New Git Pushed: {repo_name}"
    actor_display = sender or pusher or "developer"

    if repo_owner and actor_display != repo_owner:
        desc = (
            f"**New git pushed!** Collaborator **{actor_display}** pushed "
            f"**{commit_count} commit(s)** to branch `{branch}`."
        )
    elif repo_owner and actor_display == repo_owner:
        desc = (
            f"**New git pushed!** Repository owner **{repo_owner}** pushed "
            f"**{commit_count} commit(s)** to branch `{branch}`."
        )
    else:
        desc = (
            f"**New git pushed!** **{actor_display}** committed and pushed "
            f"**{commit_count} commit(s)** to branch `{branch}`."
        )

    repo_val = f"[{repo_name}](https://github.com/{repo_name})"
    if repo_owner:
        repo_val += f" • Owner: **{repo_owner}**"

    pusher_disp = (
        f"**{sender}** (pushed by `{pusher}`)"
        if sender and pusher and sender != pusher
        else f"**{actor_display}**"
    )

    fields: list[dict[str, Any]] = [
        {"name": "📦 Repository", "value": repo_val, "inline": True},
        {"name": "🌿 Branch", "value": f"`{branch}`", "inline": True},
        {"name": "👤 Pusher", "value": pusher_disp, "inline": True},
    ]

    authors: list[str] = []
    if commits:
        for c in commits:
            c_auth = c.get("author", {}) if isinstance(c.get("author"), dict) else {}
            a_name = c_auth.get("username") or c_auth.get("name")
            if a_name and a_name not in authors:
                authors.append(a_name)

    if authors:
        fields.append(
            {
                "name": "👥 Commit Author(s)",
                "value": ", ".join(f"**{a}**" for a in authors),
                "inline": True,
            }
        )

    if commits:
        c_lines = _format_commit_lines(commits, repo_name, actor_display)
        fields.append(
            {"name": "📝 Commits Committed", "value": "\n".join(c_lines), "inline": False}
        )

    if compare_url:
        fields.append(
            {
                "name": "🔍 Compare Changes",
                "value": f"[View Full Diff]({compare_url})",
                "inline": False,
            }
        )

    return title, desc, fields


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
        webhook_url: str | None = None,
    ) -> bool:
        """Sends rich embed notification to configured Discord webhook."""
        target_url = webhook_url or self.webhook_url
        if not target_url:
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
                resp = await client.post(target_url, json=payload)
                if resp.status_code in (200, 204):
                    logger.info(
                        "Discord notification sent successfully to %s: %s",
                        target_url.split("/")[-1][:12],
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
        sender: str | None = None,
        repo_owner: str | None = None,
        repo_github_id: int | None = None,
        destinations: list[str] | None = None,
    ) -> bool:
        """Sends an automated rich Discord alert when a new git push is received."""
        target_urls = set()
        if destinations:
            for d in destinations:
                if d and d.strip():
                    target_urls.add(d.strip())
        if not target_urls and self.webhook_url:
            target_urls.add(self.webhook_url)

        title, description, fields = _build_git_push_fields(
            repo_name=repo_name,
            pusher=pusher,
            branch=branch,
            commits=commits,
            compare_url=compare_url,
            sender=sender,
            repo_owner=repo_owner,
        )

        if not target_urls:
            logger.debug(
                "No custom subscriber webhooks configured for %s; dispatching to default notification handler.",
                repo_name,
            )
            return await self.send_discord_notification(
                title=title,
                description=description,
                color=0x10B981,
                fields=fields,
            )

        delivered_any = False
        for url in target_urls:
            if url == self.webhook_url:
                ok = await self.send_discord_notification(
                    title=title,
                    description=description,
                    color=0x10B981,
                    fields=fields,
                )
            else:
                ok = await self.send_discord_notification(
                    title=title,
                    description=description,
                    color=0x10B981,
                    fields=fields,
                    webhook_url=url,
                )
            if ok:
                delivered_any = True

        return delivered_any

    async def notify_git_commit(
        self,
        repo_name: str,
        author: str,
        sha: str,
        message: str,
        branch: str = "main",
        commit_url: str | None = None,
    ) -> bool:
        """Sends an automated rich Discord alert when a commit is registered."""
        if not self.webhook_url:
            return False

        sha_short = sha[:7] if sha else "head"
        url = commit_url or f"https://github.com/{repo_name}/commit/{sha_short}"
        title = f"⚡ New Git Committed: {repo_name}"
        description = f"**New git committed!** **{author}** committed to `{branch}`: **{message}**"

        fields: list[dict[str, Any]] = [
            {
                "name": "📦 Repository",
                "value": f"[{repo_name}](https://github.com/{repo_name})",
                "inline": True,
            },
            {"name": "🌿 Branch", "value": f"`{branch}`", "inline": True},
            {"name": "👤 Committer", "value": f"**{author}**", "inline": True},
            {
                "name": "📝 Commit Details",
                "value": f"• [`{sha_short}`]({url}) **committed**: {message}",
                "inline": False,
            },
        ]

        return await self.send_discord_notification(
            title=title,
            description=description,
            color=0x38BDF8,  # GitPulse Cyan
            fields=fields,
        )

    async def notify_git_pull(
        self,
        repo_name: str,
        actor: str,
        action: str,
        pr_number: int | str,
        pr_title: str,
        pr_url: str | None = None,
    ) -> bool:
        """Sends an automated rich Discord alert when a pull request is pulled / merged / updated."""
        if not self.webhook_url:
            return False

        url = pr_url or f"https://github.com/{repo_name}/pull/{pr_number}"
        title = f"📥 New Git Pulled | Pull Request {action.upper()}: {repo_name} #{pr_number}"
        description = (
            f"**New git pulled!** **{actor}** {action} pull request: **[{pr_title}]({url})**"
        )

        fields: list[dict[str, Any]] = [
            {
                "name": "📦 Repository",
                "value": f"[{repo_name}](https://github.com/{repo_name})",
                "inline": True,
            },
            {"name": "👤 Author", "value": f"**{actor}**", "inline": True},
            {"name": "📋 Status", "value": f"`{action.upper()}`", "inline": True},
            {
                "name": "🔗 PR Link",
                "value": f"[Open PR #{pr_number}]({url})",
                "inline": False,
            },
        ]

        return await self.send_discord_notification(
            title=title,
            description=description,
            color=0x8B5CF6,  # Purple for PR / pull
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
            repo_owner = repo_name.split("/")[0] if "/" in repo_name else None
            return await self.notify_git_push(
                repo_name=repo_name,
                pusher=actor,
                sender=actor,
                branch=branch,
                commits=commits,
                compare_url=compare_url,
                repo_owner=repo_owner,
            )

        if ev_type == "PullRequestEvent":
            action = payload.get("action") or "updated"
            pr = payload.get("pull_request") or {}
            pr_num = pr.get("number") or payload.get("number") or ""
            pr_title = pr.get("title") or "Pull Request"
            pr_url = pr.get("html_url") or f"https://github.com/{repo_name}/pull/{pr_num}"
            return await self.notify_git_pull(
                repo_name=repo_name,
                actor=actor,
                action=action,
                pr_number=pr_num,
                pr_title=pr_title,
                pr_url=pr_url,
            )

        if ev_type in ("CommitCommentEvent", "CommitEvent"):
            comment = payload.get("comment") or {}
            sha = comment.get("commit_id") or payload.get("sha") or "head"
            msg = comment.get("body") or payload.get("message") or "Commit note"
            return await self.notify_git_commit(
                repo_name=repo_name,
                author=actor,
                sha=sha,
                message=msg,
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
    """CLI utility invoked by Universal Git Hooks to persist activity to DB and dispatch alerts."""
    parser = argparse.ArgumentParser(description="GitPulse Activity & Discord Notification CLI")
    parser.add_argument("--webhook-url", default=None, help="Discord Webhook URL override")
    parser.add_argument("--repo", default=None, help="Repository full name (owner/repo or repo)")
    parser.add_argument("--pusher", default=None, help="Pusher / author username")
    parser.add_argument("--branch", default="main", help="Target branch")
    parser.add_argument(
        "--message", default="Automated Git push notification from GitPulse", help="Commit message"
    )
    parser.add_argument("--sha", default="head", help="Commit SHA hash")
    args = parser.parse_args()

    from backend.src.gitpulse.services.activity_service import (
        activity_service,
        resolve_effective_user,
    )

    effective_repo = args.repo or "gitpulse"
    effective_pusher = resolve_effective_user(args.pusher)
    commits = [{"id": args.sha, "message": args.message}]

    # Validate DISCORD_WEBHOOK_URL configuration
    webhook_candidate = (
        args.webhook_url or os.environ.get("DISCORD_WEBHOOK_URL") or settings.DISCORD_WEBHOOK_URL
    )
    if webhook_candidate and not str(webhook_candidate).strip():
        webhook_candidate = None

    if not webhook_candidate:
        print(
            "[GitPulse] ℹ️ DISCORD_WEBHOOK_URL is absent or unconfigured. "
            "Skipping Discord notification delivery gracefully."
        )
    else:
        # Secure format validation
        if not (
            str(webhook_candidate).startswith("https://")
            or str(webhook_candidate).startswith("http://")
        ):
            print(
                "[GitPulse] ⚠️ DISCORD_WEBHOOK_URL is invalid (must begin with http:// or https://). "
                "Skipping Discord notification delivery gracefully."
            )
            webhook_candidate = None

    # Safely persist repository, commits, and activity event into database
    try:
        res = asyncio.run(
            activity_service.record_commit_activity(
                repo=effective_repo,
                actor=effective_pusher,
                branch=args.branch,
                sha=args.sha,
                message=args.message,
                commits=commits,
                discord_webhook_url=webhook_candidate,
                notify_discord=bool(webhook_candidate),
            )
        )

        if res.get("status") == "SUCCESS":
            if res.get("delivered"):
                print(
                    f"[GitPulse] 🚀 Git activity stored in database (repo: {res.get('repository')}, "
                    f"event: {res.get('event_id')}) & Discord notification dispatched."
                )
            else:
                print(
                    f"[GitPulse] 💾 Git activity stored in database (repo: {res.get('repository')}, "
                    f"event: {res.get('event_id')}). Discord notification skipped (unconfigured or inactive)."
                )
        else:
            print(f"[GitPulse] ⚠️ Git activity completed with notice: {res}")
    except Exception as exc:
        print(
            f"[GitPulse] ⚠️ Notification dispatch encountered a non-fatal issue: {exc}. "
            f"Skipping gracefully to preserve build status."
        )


if __name__ == "__main__":
    main()
