"""Groq AI Orchestration Service for GitPulse.

Provides high-performance LLM completions and streaming using Groq models
(e.g., openai/gpt-oss-120b).
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Generator
from typing import Any

from groq import Groq

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger


class GroqAIService:
    """Service wrapping Groq SDK for AI orchestration and developer analytics."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.api_key = (
            api_key
            or settings.GROQ_API_KEY
            or os.environ.get("GROQ_API_KEY")
            or os.environ.get("groq_API_KEY")
            or ""
        )
        self.model = model or settings.GROQ_MODEL or "openai/gpt-oss-120b"
        self._client: Groq | None = None

    @property
    def client(self) -> Groq:
        """Lazy-loaded Groq client instance."""
        if self._client is None:
            if not self.api_key:
                logger.warning(
                    "Groq API key not configured. Using client with default environment lookup."
                )
                self._client = Groq()
            else:
                self._client = Groq(api_key=self.api_key)
        return self._client

    def stream_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 1.0,
        max_completion_tokens: int = 2048,
        top_p: float = 1.0,
        reasoning_effort: str = "medium",
    ) -> Generator[str, None, None]:
        """Streams completion tokens using Groq chat completions API.

        Matches exact model parameters:
        model="openai/gpt-oss-120b",
        temperature=1,
        max_completion_tokens=2048,
        top_p=1,
        reasoning_effort="medium",
        stream=True
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                top_p=top_p,
                reasoning_effort=reasoning_effort,  # type: ignore
                stream=True,
                stop=None,
            )

            for chunk in completion:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
        except Exception as exc:
            logger.error("Groq chat completion streaming error: %s", exc)
            yield f"\n[AI Service Error: {exc}]"

    def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 1.0,
        max_completion_tokens: int = 2048,
        top_p: float = 1.0,
        reasoning_effort: str = "medium",
    ) -> str:
        """Generates a complete response string by aggregating streamed tokens."""
        collected: list[str] = []
        for token in self.stream_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            top_p=top_p,
            reasoning_effort=reasoning_effort,
        ):
            collected.append(token)
        return "".join(collected)

    def analyze_repository_metrics(
        self,
        repo_full_name: str,
        metrics: dict[str, Any],
    ) -> str:
        """Generates AI insights for repository commit velocity and health."""
        system_prompt = (
            "You are GitPulse AI, an expert Principal Systems Engineer and Velocity Analyst. "
            "Analyze the given developer activity metrics and provide concise, high-value insights, "
            "bottlenecks, and recommended engineering workflow improvements."
        )
        prompt = (
            f"Repository: {repo_full_name}\n"
            f"Metrics Data:\n"
            f"- Total Commits (30d): {metrics.get('total_commits', 0)}\n"
            f"- Active Contributors: {metrics.get('active_contributors', 0)}\n"
            f"- Average PR Cycle Time: {metrics.get('avg_pr_cycle_time_hours', 0)} hours\n"
            f"- Code Churn Rate: {metrics.get('churn_rate', 0.0) * 100:.1f}%\n"
            f"- Lines Added: {metrics.get('lines_added', 0)}\n"
            f"- Lines Deleted: {metrics.get('lines_deleted', 0)}\n\n"
            "Provide a structured assessment covering: 1. Velocity Health, 2. Review Bottlenecks, 3. Strategic Action."
        )
        return self.generate_completion(prompt=prompt, system_prompt=system_prompt)


def main() -> None:
    """CLI test execution for Groq AI streaming completion."""
    parser = argparse.ArgumentParser(description="GitPulse Groq AI Streaming Tool")
    parser.add_argument(
        "--prompt",
        type=str,
        default="Explain commit velocity and code churn in GitPulse.",
        help="Prompt to submit to Groq model",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openai/gpt-oss-120b",
        help="Target Groq model identifier",
    )
    args = parser.parse_args()

    service = GroqAIService(model=args.model)
    print(f"\n--- Submitting Prompt to Groq ({args.model}) ---")
    print(f"Prompt: {args.prompt}\n")
    print("Response: ", end="", flush=True)

    for chunk in service.stream_completion(prompt=args.prompt):
        print(chunk, end="", flush=True)
    print("\n-------------------------------------------------\n")


if __name__ == "__main__":
    main()
