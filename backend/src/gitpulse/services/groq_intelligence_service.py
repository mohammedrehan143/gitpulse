"""Groq-Powered AI Engineering Intelligence Service for GitPulse.

Transforms raw GitHub activity and repository analytics into AI-powered engineering insights.
Grounds all summaries strictly in verified database facts, preventing hallucination.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from groq import Groq

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.services.ai_context_builder import AIContextBuilder


class GroqIntelligenceService:
    """Service orchestrating Groq LLM inference with strict database grounding and in-memory caching."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
    ):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = (
                settings.GROQ_API_KEY
                or os.environ.get("GROQ_API_KEY")
                or os.environ.get("groq_API_KEY")
                or ""
            )
        self.model = model or settings.GROQ_MODEL or "openai/gpt-oss-120b"
        self.timeout = timeout
        self._client: Groq | None = None
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @property
    def client(self) -> Groq:
        """Lazy-loaded Groq client."""
        if self._client is None:
            if self.api_key:
                self._client = Groq(api_key=self.api_key, timeout=self.timeout)
            else:
                self._client = Groq(timeout=self.timeout)
        return self._client

    # --------------------------------------------------------------------------
    # Cache Management
    # --------------------------------------------------------------------------
    def get_cached(self, key: str) -> dict[str, Any] | None:
        """Returns cached payload if within TTL."""
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < 900:  # 15 minute TTL
                data_copy = dict(data)
                data_copy["cached"] = True
                return data_copy
            del self._cache[key]
        return None

    def set_cached(self, key: str, data: dict[str, Any]) -> None:
        """Stores payload in cache."""
        self._cache[key] = (time.time(), data)

    # --------------------------------------------------------------------------
    # Helper: JSON extraction & LLM invocation
    # --------------------------------------------------------------------------
    def _call_groq_json(
        self,
        prompt: str,
        system_prompt: str,
    ) -> dict[str, Any] | None:
        """Calls Groq API expecting a structured JSON response."""
        if not self.api_key:
            return None

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                temperature=0.2,
                max_completion_tokens=2048,
                top_p=1.0,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as exc:
            logger.warning(
                "Groq structured completion failed: %s; activating grounded rule engine", exc
            )
            return None

    @staticmethod
    def _extract_json_from_text(text: str) -> dict[str, Any] | None:
        """Extracts JSON object from text containing possible markdown formatting."""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return None

    # --------------------------------------------------------------------------
    # 1. Repository Intelligence
    # --------------------------------------------------------------------------
    async def generate_repository_intelligence(
        self,
        owner: str,
        repo: str,
        timeframe_days: int = 30,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Generates grounded repository health, activity, and cadence intelligence."""
        cache_key = f"repo_intel:{owner}/{repo}:{timeframe_days}"
        if not force_refresh:
            cached = self.get_cached(cache_key)
            if cached:
                return cached

        context = await AIContextBuilder.get_repository_context(owner, repo, days=timeframe_days)
        if "error" in context:
            return context

        system_prompt = (
            "You are GitPulse Senior Engineering Intelligence Analyst. "
            "Analyze the verified repository telemetry. "
            "STRICT GROUNDING RULE: Never invent facts, numbers, or contributors. "
            "Distinguish verified database facts from your AI interpretations. "
            "Output must be valid JSON with keys: "
            "'health_summary' (string), "
            "'activity_analysis' (string), "
            "'inactive_periods_detected' (string), "
            "'unusual_patterns' (array of strings), "
            "'recent_progress_summary' (string), "
            "'strategic_recommendations' (array of strings), "
            "'ai_interpretations' (array of strings), "
            "'missing_or_unavailable' (array of strings)."
        )

        prompt = (
            f"Repository: {context['repository']}\n"
            f"Timeframe: Last {timeframe_days} days\n"
            f"Data Freshness: {context['data_freshness']}\n\n"
            f"Verified Facts:\n{json.dumps(context['verified_facts'], indent=2)}\n\n"
            f"Recent Commits Sample:\n{json.dumps(context['samples']['recent_commits'], indent=2)}\n\n"
            f"Long-Running PRs:\n{json.dumps(context['samples']['long_running_prs'], indent=2)}\n\n"
            f"Top Contributors:\n{json.dumps(context['samples']['top_contributors'], indent=2)}\n\n"
            "Generate repository intelligence in the specified JSON structure."
        )

        ai_result = self._call_groq_json(prompt, system_prompt)
        is_fallback = False
        if not ai_result:
            ai_result = self._fallback_repository_intelligence(context)
            is_fallback = True

        result: dict[str, Any] = {
            "repository": context["repository"],
            "timeframe_days": timeframe_days,
            "data_freshness": context["data_freshness"],
            "source": "grounded_rule_engine" if is_fallback or not self.api_key else "groq_llm",
            "verified_facts": context["verified_facts"],
            "health_summary": ai_result.get("health_summary", ""),
            "activity_analysis": ai_result.get("activity_analysis", ""),
            "inactive_periods_detected": ai_result.get("inactive_periods_detected", ""),
            "unusual_patterns": ai_result.get("unusual_patterns", []),
            "recent_progress_summary": ai_result.get("recent_progress_summary", ""),
            "strategic_recommendations": ai_result.get("strategic_recommendations", []),
            "ai_interpretations": ai_result.get("ai_interpretations", []),
            "missing_or_unavailable": ai_result.get("missing_or_unavailable", []),
            "cached": False,
        }

        self.set_cached(cache_key, result)
        return result

    @staticmethod
    def _fallback_repository_intelligence(context: dict[str, Any]) -> dict[str, Any]:
        """Deterministic grounded fallback for repository intelligence."""
        facts = context.get("verified_facts", {})
        commits = facts.get("total_commits", 0)
        open_prs = facts.get("open_prs_count", 0)
        long_running = facts.get("long_running_prs_count", 0)
        inactive = facts.get("inactive_days", 0)
        churn = facts.get("code_churn_rate", 0.0)

        health = "Healthy"
        if long_running > 3 or inactive > 15:
            health = "Needs Attention"
        elif commits == 0:
            health = "Inactive"

        unusual = []
        if churn > 0.4:
            unusual.append(
                f"Elevated code churn rate at {int(churn * 100)}% indicates substantial refactoring or discarded code."
            )
        if long_running > 0:
            unusual.append(f"{long_running} pull request(s) have been open for more than 7 days.")
        if inactive > 10:
            unusual.append(
                f"Detected {inactive} inactive calendar days out of {context.get('timeframe_days', 30)} days."
            )

        recommendations = []
        if long_running > 0:
            recommendations.append(
                "Triage and review stalled pull requests to unblock ongoing feature streams."
            )
        if commits > 0 and open_prs == 0:
            recommendations.append(
                "Ensure peer review workflows are followed for direct master/main pushes."
            )
        if not recommendations:
            recommendations.append("Maintain steady release cadence and monitor test pass rates.")

        return {
            "health_summary": f"Repository is categorized as '{health}' with {commits} commits and {open_prs} open PRs.",
            "activity_analysis": f"Recorded {commits} commits by {facts.get('active_authors_count', 0)} active authors over the last {context.get('timeframe_days', 30)} days.",
            "inactive_periods_detected": f"{inactive} days without recorded commits detected in timeframe.",
            "unusual_patterns": unusual
            or ["No anomalous velocity spikes or unusual churn detected."],
            "recent_progress_summary": f"Successfully ingested {facts.get('lines_added', 0)} lines added and {facts.get('lines_deleted', 0)} lines deleted.",
            "strategic_recommendations": recommendations,
            "ai_interpretations": [
                "Health category determined by commit cadence and PR review delay metrics.",
                "Inactivity calculation based on days with zero recorded commit activity.",
            ],
            "missing_or_unavailable": [
                "CI/CD workflow run statuses not ingested for this repository.",
                "Deep static code analysis diffs unavailable in basic event schema.",
            ],
        }

    # --------------------------------------------------------------------------
    # 2. Pull Request Intelligence
    # --------------------------------------------------------------------------
    async def generate_pr_intelligence(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Generates pull request complexity, review risk, and activity intelligence."""
        cache_key = f"pr_intel:{owner}/{repo}:{pr_number}"
        if not force_refresh:
            cached = self.get_cached(cache_key)
            if cached:
                return cached

        context = await AIContextBuilder.get_pr_context(owner, repo, pr_number)
        if "error" in context:
            return context

        system_prompt = (
            "You are GitPulse PR Risk Analyst. Analyze the pull request telemetry. "
            "STRICT RULES: "
            "1. Do not claim deep security vulnerability detection unless full code diffs are provided. "
            "2. Ground analysis in lines changed, review delays, and discussion counts. "
            "3. Output valid JSON with keys: "
            "'pr_summary' (string), "
            "'risk_level' ('LOW' | 'MEDIUM' | 'HIGH'), "
            "'risk_factors' (array of strings), "
            "'review_activity_analysis' (string), "
            "'long_running_flag' (boolean), "
            "'recommendations' (array of strings), "
            "'ai_interpretations' (array of strings), "
            "'missing_or_unavailable' (array of strings)."
        )

        prompt = (
            f"PR #{pr_number} - {context['title']}\n"
            f"Repository: {context['repository']}\n"
            f"Author: {context['author']}\n"
            f"State: {context['state']}\n"
            f"Created At: {context['created_at']}\n"
            f"Description:\n{context['body']}\n\n"
            f"Verified Metrics:\n{json.dumps(context['verified_metrics'], indent=2)}\n\n"
            f"Review Timeline:\n{json.dumps(context['reviews'], indent=2)}\n\n"
            "Assess PR complexity, review risk, and turnaround."
        )

        ai_result = self._call_groq_json(prompt, system_prompt)
        is_fallback = False
        if not ai_result:
            ai_result = self._fallback_pr_intelligence(context)
            is_fallback = True

        result: dict[str, Any] = {
            "repository": context["repository"],
            "number": pr_number,
            "title": context["title"],
            "state": context["state"],
            "author": context["author"],
            "source": "grounded_rule_engine" if is_fallback or not self.api_key else "groq_llm",
            "verified_metrics": context["verified_metrics"],
            "pr_summary": ai_result.get("pr_summary", ""),
            "risk_level": ai_result.get("risk_level", "LOW"),
            "risk_factors": ai_result.get("risk_factors", []),
            "review_activity_analysis": ai_result.get("review_activity_analysis", ""),
            "long_running_flag": ai_result.get("long_running_flag", False),
            "recommendations": ai_result.get("recommendations", []),
            "ai_interpretations": ai_result.get("ai_interpretations", []),
            "missing_or_unavailable": ai_result.get("missing_or_unavailable", []),
            "cached": False,
        }

        self.set_cached(cache_key, result)
        return result

    @staticmethod
    def _fallback_pr_intelligence(context: dict[str, Any]) -> dict[str, Any]:
        """Deterministic grounded fallback for PR intelligence."""
        metrics = context.get("verified_metrics", {})
        total_changes = metrics.get("total_changes", 0)
        files = metrics.get("changed_files", 0)
        reviews_count = metrics.get("reviews_count", 0)
        delay = context.get("first_review_delay_hours")

        risk_level = "LOW"
        risk_factors = []
        if total_changes > 1000 or files > 20:
            risk_level = "HIGH"
            risk_factors.append(
                f"Large diff surface area ({total_changes} lines, {files} files) increases review complexity."
            )
        elif total_changes > 400 or files > 10:
            risk_level = "MEDIUM"
            risk_factors.append(f"Moderate diff ({total_changes} lines across {files} files).")

        if delay and delay > 48:
            risk_factors.append(f"First review turnaround took {delay} hours.")

        if reviews_count == 0 and context.get("state") == "open":
            risk_factors.append("No peer review submissions recorded yet.")

        return {
            "pr_summary": f"Pull request '{context.get('title')}' by {context.get('author')}. State: {context.get('state')}.",
            "risk_level": risk_level,
            "risk_factors": risk_factors
            or ["Diff size and file count are within normal low-risk bounds."],
            "review_activity_analysis": f"{reviews_count} formal reviews recorded with {metrics.get('review_comments_count', 0)} review comments.",
            "long_running_flag": (delay is not None and delay > 72),
            "recommendations": [
                "Break large pull requests into smaller atomic reviewable units when possible.",
                "Ensure CI verification passes before scheduling review merge.",
            ],
            "ai_interpretations": [
                "Risk level scored using diff line count, file breadth, and initial review delay."
            ],
            "missing_or_unavailable": [
                "Full unified diff patches not stored locally; analysis restricted to metadata metrics."
            ],
        }

    # --------------------------------------------------------------------------
    # 3. Developer Intelligence
    # --------------------------------------------------------------------------
    async def generate_developer_intelligence(
        self,
        owner: str,
        repo: str,
        developer_login: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Generates evidence-based developer contribution summaries without misleading scores."""
        cache_key = f"dev_intel:{owner}/{repo}:{developer_login}"
        if not force_refresh:
            cached = self.get_cached(cache_key)
            if cached:
                return cached

        context = await AIContextBuilder.get_developer_context(owner, repo, developer_login)
        if "error" in context:
            return context

        system_prompt = (
            "You are GitPulse Engineering Velocity Analyst. "
            "Analyze the developer's verified contribution records. "
            "CRITICAL POLICIES: "
            "1. NEVER generate misleading productivity scores, developer rankings, or gamified grades. "
            "2. Provide strictly evidence-based contribution summaries referencing actual commits and PRs. "
            "3. Output valid JSON with keys: "
            "'contribution_summary' (string), "
            "'commit_and_pr_patterns' (string), "
            "'contribution_trends' (string), "
            "'evidence_notes' (array of strings), "
            "'ai_interpretations' (array of strings), "
            "'missing_or_unavailable' (array of strings)."
        )

        prompt = (
            f"Developer: {developer_login}\n"
            f"Repository: {context['repository']}\n"
            f"Verified Metrics:\n{json.dumps(context['verified_metrics'], indent=2)}\n\n"
            f"Recent Commits:\n{json.dumps(context['recent_commits'], indent=2)}\n\n"
            f"Recent PRs:\n{json.dumps(context['recent_prs'], indent=2)}\n\n"
            "Generate an objective, evidence-grounded engineering summary."
        )

        ai_result = self._call_groq_json(prompt, system_prompt)
        is_fallback = False
        if not ai_result:
            ai_result = self._fallback_developer_intelligence(context)
            is_fallback = True

        result: dict[str, Any] = {
            "repository": context["repository"],
            "developer": developer_login,
            "source": "grounded_rule_engine" if is_fallback or not self.api_key else "groq_llm",
            "verified_metrics": context["verified_metrics"],
            "contribution_summary": ai_result.get("contribution_summary", ""),
            "commit_and_pr_patterns": ai_result.get("commit_and_pr_patterns", ""),
            "contribution_trends": ai_result.get("contribution_trends", ""),
            "evidence_notes": ai_result.get("evidence_notes", []),
            "ai_interpretations": ai_result.get("ai_interpretations", []),
            "missing_or_unavailable": ai_result.get("missing_or_unavailable", []),
            "cached": False,
        }

        self.set_cached(cache_key, result)
        return result

    @staticmethod
    def _fallback_developer_intelligence(context: dict[str, Any]) -> dict[str, Any]:
        """Deterministic grounded fallback for developer intelligence."""
        m = context.get("verified_metrics", {})
        commits_cnt = m.get("commits_count", 0)
        prs_cnt = m.get("prs_authored_count", 0)
        merged_cnt = m.get("prs_merged_count", 0)
        dev = context.get("developer", "developer")

        return {
            "contribution_summary": f"Developer '{dev}' has contributed {commits_cnt} recent commits and authored {prs_cnt} pull requests ({merged_cnt} merged).",
            "commit_and_pr_patterns": f"Generated {m.get('lines_added', 0)} line additions and {m.get('lines_deleted', 0)} deletions across tracked changes.",
            "contribution_trends": f"Active from {m.get('first_active') or 'N/A'} to {m.get('last_active') or 'N/A'}.",
            "evidence_notes": [
                f"Verified {commits_cnt} commits in local GitPulse database.",
                f"Verified {prs_cnt} pull requests with {merged_cnt} merged to default branch.",
            ],
            "ai_interpretations": [
                "Summaries strictly track verified commit and PR volume without subjective scoring."
            ],
            "missing_or_unavailable": [
                "Code review submissions and inline comments authored by this user not aggregated in developer card."
            ],
        }

    # --------------------------------------------------------------------------
    # 4. Team Intelligence
    # --------------------------------------------------------------------------
    async def generate_team_intelligence(
        self,
        owner: str,
        repo: str,
        timeframe_days: int = 7,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Generates weekly team engineering reports, distribution, and bottleneck analysis."""
        cache_key = f"team_intel:{owner}/{repo}:{timeframe_days}"
        if not force_refresh:
            cached = self.get_cached(cache_key)
            if cached:
                return cached

        context = await AIContextBuilder.get_repository_context(owner, repo, days=timeframe_days)
        if "error" in context:
            return context

        system_prompt = (
            "You are GitPulse Lead Systems Architect. "
            "Generate a weekly team engineering report based strictly on the provided verified metrics. "
            "Output valid JSON with keys: "
            "'weekly_report' (string), "
            "'contribution_distribution_analysis' (string), "
            "'review_bottlenecks' (array of strings), "
            "'collaboration_patterns' (string), "
            "'team_recommendations' (array of strings), "
            "'ai_interpretations' (array of strings), "
            "'missing_or_unavailable' (array of strings)."
        )

        prompt = (
            f"Repository: {context['repository']}\n"
            f"Report Window: Last {timeframe_days} days\n"
            f"Verified Facts:\n{json.dumps(context['verified_facts'], indent=2)}\n\n"
            f"Top Contributors:\n{json.dumps(context['samples']['top_contributors'], indent=2)}\n\n"
            f"Long-Running PRs:\n{json.dumps(context['samples']['long_running_prs'], indent=2)}\n\n"
            "Generate a grounded team engineering report."
        )

        ai_result = self._call_groq_json(prompt, system_prompt)
        is_fallback = False
        if not ai_result:
            ai_result = self._fallback_team_intelligence(context)
            is_fallback = True

        result: dict[str, Any] = {
            "repository": context["repository"],
            "timeframe_days": timeframe_days,
            "data_freshness": context["data_freshness"],
            "source": "grounded_rule_engine" if is_fallback or not self.api_key else "groq_llm",
            "weekly_report": ai_result.get("weekly_report", ""),
            "contribution_distribution_analysis": ai_result.get(
                "contribution_distribution_analysis", ""
            ),
            "review_bottlenecks": ai_result.get("review_bottlenecks", []),
            "collaboration_patterns": ai_result.get("collaboration_patterns", ""),
            "team_recommendations": ai_result.get("team_recommendations", []),
            "ai_interpretations": ai_result.get("ai_interpretations", []),
            "missing_or_unavailable": ai_result.get("missing_or_unavailable", []),
            "cached": False,
        }

        self.set_cached(cache_key, result)
        return result

    @staticmethod
    def _fallback_team_intelligence(context: dict[str, Any]) -> dict[str, Any]:
        """Deterministic grounded fallback for team engineering report."""
        facts = context.get("verified_facts", {})
        long_running = facts.get("long_running_prs_count", 0)
        active_authors = facts.get("active_authors_count", 0)
        cycle_hours = facts.get("avg_pr_cycle_time_hours", 0.0)

        bottlenecks = []
        if long_running > 0:
            bottlenecks.append(
                f"{long_running} PR(s) open for >7 days may indicate review bandwidth constraints."
            )
        if cycle_hours > 72:
            bottlenecks.append(
                f"Average PR cycle time of {cycle_hours} hours exceeds the 48-hour healthy SLA."
            )

        return {
            "weekly_report": (
                f"Engineering weekly report for {context.get('repository')}: "
                f"{facts.get('total_commits', 0)} commits delivered across {active_authors} active team member(s). "
                f"{facts.get('open_prs_count', 0)} open PRs currently in flight."
            ),
            "contribution_distribution_analysis": f"Active contribution spread across {active_authors} developers.",
            "review_bottlenecks": bottlenecks
            or ["No critical review bottlenecks detected in current cycle."],
            "collaboration_patterns": f"Team completed {facts.get('merged_prs_count', 0)} merged PRs with avg cycle time of {cycle_hours} hours.",
            "team_recommendations": [
                "Establish daily PR triage to prevent review delays.",
                "Balance code review workload across all available team engineers.",
            ],
            "ai_interpretations": [
                "Team velocity evaluated from commit aggregation and pull request throughput."
            ],
            "missing_or_unavailable": [
                "Team pairing and synchronous meetings data is not tracked by GitHub."
            ],
        }

    # --------------------------------------------------------------------------
    # 5. AI Engineering Assistant (Natural-Language QA)
    # --------------------------------------------------------------------------
    async def query_engineering_assistant(
        self,
        question: str,
        target_repo: str | None = None,
    ) -> dict[str, Any]:
        """Answers natural-language engineering questions strictly grounded in GitPulse database facts."""
        q_clean = question.strip()
        timeframe_days = 7
        if any(w in q_clean.lower() for w in ["month", "30 days", "monthly"]):
            timeframe_days = 30

        # Retrieve grounded context
        global_context = await AIContextBuilder.get_global_engineering_context(days=timeframe_days)
        repo_context: dict[str, Any] | None = None

        if target_repo and "/" in target_repo:
            parts = target_repo.split("/", 1)
            repo_context = await AIContextBuilder.get_repository_context(
                parts[0], parts[1], days=timeframe_days
            )

        if repo_context and "error" not in repo_context:
            system_prompt = (
                "You are GitPulse Senior AI Engineering Assistant. "
                "The engineer is asking a question about their selected repository. "
                f"STRICT TARGET FOCUS: The user has selected the specific repository '{target_repo}'. "
                "YOUR ENTIRE ANSWER MUST BE GROUNDED IN AND PRIMARILY FOCUSED ON THIS SPECIFIC REPOSITORY. "
                "1. State the exact commit count (both all-time commits and timeframe commits), pull requests count (open and merged), "
                "   issues, code volume (+lines added, -lines deleted), and the latest commit details (message, author, timestamp). "
                "2. If zero commits were pushed in the recent 7-day window, explicitly explain: "
                "   'In the active 7-day window there were 0 new commits pushed, but across repository history, "
                "   <primary_contributor> has authored <all_time_commits_count> commits, <total_pull_requests_count> PRs, and <total_issues_count> issues "
                '   (last active on <latest_commit_date> with commit "<latest_commit_message>").\' '
                "3. Never claim 0 commits or 0 PRs if the verified facts show all_time_commits_count or total_pull_requests_count > 0. "
                "4. Do NOT ramble about external/unrelated repositories unless specifically requested. "
                "5. Output valid JSON with keys: "
                "'answer' (detailed string), "
                "'verified_facts' (object with referenced metrics), "
                "'calculated_metrics' (object with derived values), "
                "'ai_interpretations' (array of strings), "
                "'missing_or_unavailable' (array of strings), "
                "'timeframe' (string), "
                "'data_freshness' (string)."
            )
            prompt = (
                f"User Question: {question}\n\n"
                f"PRIMARY SELECTED REPOSITORY: {target_repo}\n"
                f"Selected Repository Telemetry & Facts:\n{json.dumps(repo_context, indent=2)}\n\n"
                f"CRITICAL DIRECTIVE: Answer the question with primary focus on {target_repo}. "
                f"Include its exact commit count, pull requests, issues, and developer contribution history. "
                f"Do not distract with unrelated repositories."
            )
        else:
            system_prompt = (
                "You are GitPulse AI Engineering Assistant. "
                "You provide answers to natural language questions regarding all monitored repositories. "
                "STRICT GROUNDING RULES: "
                "1. You must ONLY answer using the verified facts provided below. "
                "2. Never invent commits, PRs, authors, repositories, or metrics. "
                "3. If requested information is missing or not present in the data, explicitly state it is unavailable. "
                "4. Structure response in valid JSON with keys: "
                "'answer' (detailed string), "
                "'verified_facts' (object with referenced metrics), "
                "'calculated_metrics' (object with derived values), "
                "'ai_interpretations' (array of strings), "
                "'missing_or_unavailable' (array of strings), "
                "'timeframe' (string), "
                "'data_freshness' (string)."
            )
            prompt = (
                f"User Question: {question}\n\n"
                f"Global Context ({timeframe_days} days):\n{json.dumps(global_context, indent=2)}\n\n"
                "Provide an accurate, grounded answer strictly based on this data."
            )

        ai_result = self._call_groq_json(prompt, system_prompt)
        is_fallback = False
        if not ai_result or not ai_result.get("answer"):
            ai_result = self._fallback_engineering_assistant(
                question=question,
                target_repo=target_repo,
                global_context=global_context,
                repo_context=repo_context,
                timeframe_days=timeframe_days,
            )
            is_fallback = True

        return {
            "question": question,
            "target_repo": target_repo,
            "source": "grounded_rule_engine" if is_fallback or not self.api_key else "groq_llm",
            "answer": ai_result.get("answer", ""),
            "verified_facts": ai_result.get("verified_facts", {}),
            "calculated_metrics": ai_result.get("calculated_metrics", {}),
            "ai_interpretations": ai_result.get("ai_interpretations", []),
            "missing_or_unavailable": ai_result.get("missing_or_unavailable", []),
            "timeframe": ai_result.get("timeframe", f"Last {timeframe_days} days"),
            "data_freshness": global_context.get("generated_at", ""),
        }

    @staticmethod
    def _fallback_engineering_assistant(
        question: str,
        target_repo: str | None,
        global_context: dict[str, Any],
        repo_context: dict[str, Any] | None,
        timeframe_days: int,
    ) -> dict[str, Any]:
        """Deterministic grounded fallback for AI Engineering Assistant."""
        q = question.lower()
        repos = global_context.get("repositories", [])
        longest_prs = global_context.get("longest_open_pull_requests", [])

        verified: dict[str, Any] = {
            "total_monitored_repos": len(repos),
        }
        calculated: dict[str, Any] = {}
        interpretations: list[str] = []
        missing: list[str] = []
        answer = ""

        # Specific repository focus if target_repo is selected and question is not cross-repo
        if (
            repo_context
            and "verified_facts" in repo_context
            and not any(w in q for w in ["across all", "compare all", "every repo"])
        ):
            rf = repo_context["verified_facts"]
            r_name = repo_context.get("repository", target_repo)
            all_commits = rf.get("all_time_commits_count", rf.get("total_commits", 0))
            all_prs = rf.get(
                "total_pull_requests_count",
                rf.get("open_prs_count", 0) + rf.get("merged_prs_count", 0),
            )
            all_issues = rf.get("total_issues_count", rf.get("open_issues_count", 0))
            win_commits = rf.get("window_commits_count", 0)
            author = rf.get("latest_commit_author", "developer")
            date = rf.get("latest_commit_date", "N/A")
            msg = rf.get("latest_commit_message", "N/A")
            added = rf.get("all_time_lines_added", rf.get("lines_added", 0))
            deleted = rf.get("all_time_lines_deleted", rf.get("lines_deleted", 0))

            answer = (
                f"Engineering activity summary for **{r_name}**:\n"
                f"- **All-Time Commits**: {all_commits} commits authored across repository history.\n"
                f"- **Pull Requests**: {all_prs} total pull requests ({rf.get('open_prs_count', 0)} open, {rf.get('merged_prs_count', 0)} merged).\n"
                f"- **Issues**: {all_issues} total issues ({rf.get('open_issues_count', 0)} open, {rf.get('closed_issues_count', 0)} closed).\n"
                f"- **Code Volume**: +{added:,} lines added, -{deleted:,} lines deleted.\n"
                f'- **Latest Commit**: "{msg}" by @{author} on {date}.\n'
            )
            if win_commits == 0:
                answer += f"\n*In the rolling {timeframe_days}-day window there were 0 new commits pushed; all {all_commits} commits and {all_prs} PRs are preserved in GitPulse's database.*"
            else:
                answer += f"\n*{win_commits} commit(s) were recorded within the active {timeframe_days}-day window.*"

            verified.update(rf)
            verified["target_repository"] = r_name
            return {
                "source": "grounded_rule_engine",
                "answer": answer,
                "verified_facts": verified,
                "calculated_metrics": calculated,
                "ai_interpretations": [
                    "Repository summary derived directly from local database records."
                ],
                "missing_or_unavailable": ["Private branch stashes not pushed to remote."],
                "timeframe": f"Last {timeframe_days} days (plus full repository history)",
            }

        # Pattern 1: Longest open PRs
        if "pr" in q and ("longest" in q or "stalled" in q or "oldest" in q):
            if longest_prs:
                lines = [
                    f"- {p['repo']} PR #{p['number']} ('{p['title']}') by @{p['author']}, created on {p['created_at']}"
                    for p in longest_prs
                ]
                answer = (
                    "Here are the longest open pull requests currently tracked in GitPulse:\n"
                    + "\n".join(lines)
                )
                verified["longest_open_prs"] = longest_prs
            else:
                answer = "There are currently no open pull requests recorded in the database."

        # Pattern 2: Inactive repositories
        elif "inactive" in q:
            inactive_repos = [r["name"] for r in repos if r["commits_in_window"] == 0]
            if inactive_repos:
                answer = f"The following repositories have been inactive (zero recorded commit activity over the last {timeframe_days} days): {', '.join(inactive_repos)}."
                verified["inactive_repositories"] = inactive_repos
            else:
                answer = f"All {len(repos)} monitored repositories have recorded commit activity in the last {timeframe_days} days."

        # Pattern 3: Latest / Recent contributors or who contributed
        elif "who" in q or "contribut" in q:
            active_repos = [
                r
                for r in repos
                if r.get("latest_commit_author") and r.get("latest_commit_author") != "None"
            ]
            if active_repos:
                lines = [
                    f"- {r['name']}: latest commit by @{r['latest_commit_author']} (last active {r['last_activity']})"
                    for r in active_repos
                ]
                answer = "Recent contribution activity recorded across repositories:\n" + "\n".join(
                    lines
                )
                verified["recent_contributors"] = [r["latest_commit_author"] for r in active_repos]
            else:
                answer = "No recent contributor commits found in the database."

        # Pattern 4: Weekly / general summary
        else:
            total_commits = sum(r["commits_in_window"] for r in repos)
            total_open_prs = sum(r["open_prs"] for r in repos)
            answer = (
                f"Engineering activity summary for the last {timeframe_days} days: "
                f"GitPulse is tracking {len(repos)} repository(ies) with a combined total of {total_commits} commits "
                f"and {total_open_prs} open pull requests in flight. "
            )
            if repo_context and "verified_facts" in repo_context:
                rf = repo_context["verified_facts"]
                answer += f"In {repo_context['repository']}, there were {rf.get('total_commits', 0)} commits and {rf.get('open_prs_count', 0)} open PRs."
                verified.update(rf)
            verified["total_commits_in_window"] = total_commits
            verified["total_open_prs"] = total_open_prs
            calculated["avg_commits_per_repo"] = round(total_commits / max(1, len(repos)), 1)

        interpretations.append(
            "Response derived from local SQLite/Supabase synchronization records."
        )
        missing.append(
            "Private internal communications and CI build logs outside GitHub are not accessible."
        )

        return {
            "source": "grounded_rule_engine",
            "answer": answer,
            "verified_facts": verified,
            "calculated_metrics": calculated,
            "ai_interpretations": interpretations,
            "missing_or_unavailable": missing,
            "timeframe": f"Last {timeframe_days} days",
        }


# Singleton service instance
groq_intelligence_service = GroqIntelligenceService()
