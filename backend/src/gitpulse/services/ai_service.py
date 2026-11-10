"""Groq AI Orchestration Service for GitPulse.

Provides high-performance LLM completions and streaming using Groq models
(e.g., openai/gpt-oss-120b).
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Generator
from typing import Any

import groq
from groq import Groq

from backend.src.gitpulse.common.config import settings
from backend.src.gitpulse.common.logging import logger


class AIServiceException(Exception):
    """Base exception for AI service operations."""

    def __init__(
        self,
        message: str,
        category: str = "EXTERNAL_AI_ERROR",
        status_code: int = 502,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.status_code = status_code


class AIConfigurationError(AIServiceException):
    """Raised when required AI configuration (e.g. GROQ_API_KEY) is missing."""

    def __init__(self, message: str = "GROQ_API_KEY is not configured"):
        super().__init__(message, category="CONFIGURATION_ERROR", status_code=503)


class AIAuthenticationError(AIServiceException):
    """Raised when Groq rejects credentials with 401."""

    def __init__(
        self, message: str = "Groq authentication failed. Check GROQ_API_KEY credentials."
    ):
        super().__init__(message, category="AUTHENTICATION_ERROR", status_code=502)


class AIModelError(AIServiceException):
    """Raised when the specified Groq model is invalid or unavailable."""

    def __init__(self, message: str = "Configured Groq model is invalid or unavailable."):
        super().__init__(message, category="MODEL_ERROR", status_code=502)


class AIRateLimitError(AIServiceException):
    """Raised when Groq API rate limit or quota is exceeded."""

    def __init__(self, message: str = "Groq API rate limit or quota exceeded."):
        super().__init__(message, category="RATE_LIMIT_ERROR", status_code=429)


class AITimeoutError(AIServiceException):
    """Raised when Groq API request times out."""

    def __init__(self, message: str = "Groq API request timed out."):
        super().__init__(message, category="TIMEOUT_ERROR", status_code=504)


class AIEmptyResponseError(AIServiceException):
    """Raised when Groq API returns an empty response."""

    def __init__(self, message: str = "Groq API returned an empty completion response."):
        super().__init__(message, category="EMPTY_RESPONSE_ERROR", status_code=502)


class AIMalformedResponseError(AIServiceException):
    """Raised when Groq API returns an unparseable or malformed response."""

    def __init__(self, message: str = "Groq API returned a malformed response."):
        super().__init__(message, category="MALFORMED_RESPONSE_ERROR", status_code=502)


class GroqAIService:
    """Service wrapping Groq SDK for AI orchestration and developer analytics."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 15.0,
    ):
        self.api_key = (
            api_key
            if api_key is not None
            else (
                settings.GROQ_API_KEY
                or os.environ.get("GROQ_API_KEY")
                or os.environ.get("groq_API_KEY")
                or ""
            )
        )
        self.model = model or settings.GROQ_MODEL or "openai/gpt-oss-120b"
        self.timeout = timeout
        self._client: Groq | None = None

    @property
    def client(self) -> Groq:
        """Lazy-loaded Groq client instance."""
        if self._client is None:
            if not self.api_key:
                logger.warning(
                    "Groq API key not configured. Using client with default environment lookup."
                )
                self._client = Groq(timeout=self.timeout)
            else:
                self._client = Groq(api_key=self.api_key, timeout=self.timeout)
        return self._client

    def _handle_bad_request(self, exc: groq.BadRequestError, create_kwargs: dict[str, Any]) -> Any:
        if "reasoning_effort" in str(exc).lower() and "reasoning_effort" in create_kwargs:
            del create_kwargs["reasoning_effort"]
            try:
                return self.client.chat.completions.create(**create_kwargs)
            except Exception as retry_exc:
                raise AIModelError(
                    f"Invalid request parameters for Groq model '{self.model}': {retry_exc}"
                ) from retry_exc
        logger.error("Groq bad request: %s", exc)
        raise AIModelError(f"Groq rejected request for model '{self.model}': {exc}") from exc

    def _handle_unexpected_groq_error(self, exc: Exception) -> None:
        if isinstance(exc, groq.APIConnectionError):
            logger.error("Groq connection failure: %s", exc)
            raise AIServiceException(
                "Unable to connect to Groq AI service.",
                category="CONNECTION_ERROR",
                status_code=503,
            ) from exc
        if isinstance(exc, groq.GroqError):
            logger.error("Groq SDK error: %s", exc)
            raise AIServiceException(
                f"Groq AI service error: {exc}",
                category="EXTERNAL_AI_ERROR",
                status_code=502,
            ) from exc
        logger.error("Unexpected error in Groq client: %s", exc)
        raise AIServiceException(
            f"Unexpected AI error: {exc}",
            category="INTERNAL_AI_ERROR",
            status_code=500,
        ) from exc

    def _create_completion(self, create_kwargs: dict[str, Any]) -> Any:
        """Executes completion request against Groq SDK with categorized exception mapping."""
        try:
            return self.client.chat.completions.create(**create_kwargs)
        except groq.AuthenticationError as exc:
            logger.error("Groq authentication failure: %s", exc)
            raise AIAuthenticationError(
                "Groq authentication failed. Please verify GROQ_API_KEY credentials."
            ) from exc
        except groq.RateLimitError as exc:
            logger.warning("Groq rate limit exceeded: %s", exc)
            raise AIRateLimitError(
                "Groq API rate limit or quota exceeded. Please retry after a brief delay."
            ) from exc
        except (groq.APITimeoutError, TimeoutError) as exc:
            logger.warning("Groq request timed out: %s", exc)
            raise AITimeoutError("Groq API request timed out.") from exc
        except groq.NotFoundError as exc:
            logger.error("Groq model not found (%s): %s", self.model, exc)
            raise AIModelError(
                f"Configured Groq model '{self.model}' is not available or invalid."
            ) from exc
        except groq.BadRequestError as exc:
            return self._handle_bad_request(exc, create_kwargs)
        except (groq.APIConnectionError, groq.GroqError, Exception) as exc:
            self._handle_unexpected_groq_error(exc)

    def _yield_chunks(self, completion: Any) -> Generator[str, None, None]:
        """Safely parses streaming chunk delta content from Groq response stream."""
        try:
            for chunk in completion:
                if not hasattr(chunk, "choices") or not chunk.choices:
                    continue
                delta = getattr(chunk.choices[0], "delta", None)
                if delta is None:
                    continue
                content = getattr(delta, "content", None)
                if content:
                    yield content
        except (groq.APITimeoutError, TimeoutError) as exc:
            logger.warning("Groq streaming chunk timed out: %s", exc)
            raise AITimeoutError("Groq streaming timed out.") from exc
        except AIServiceException:
            raise
        except Exception as exc:
            logger.error("Error reading Groq stream: %s", exc)
            raise AIMalformedResponseError(f"Error reading Groq response stream: {exc}") from exc

    def stream_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 1.0,
        max_completion_tokens: int = 2048,
        top_p: float = 1.0,
        reasoning_effort: str = "medium",
    ) -> Generator[str, None, None]:
        """Streams completion tokens using Groq chat completions API."""
        if not self.api_key and self._client is None:
            raise AIConfigurationError(
                "GROQ_API_KEY is not configured in backend environment or settings"
            )

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,  # type: ignore
            "temperature": temperature,
            "max_completion_tokens": max_completion_tokens,
            "top_p": top_p,
            "stream": True,
            "stop": None,
        }
        if reasoning_effort and (
            "oss" in self.model.lower()
            or "o1" in self.model.lower()
            or "o3" in self.model.lower()
            or "reasoning" in self.model.lower()
        ):
            create_kwargs["reasoning_effort"] = reasoning_effort

        completion = self._create_completion(create_kwargs)
        yield from self._yield_chunks(completion)

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
        result = "".join(collected).strip()
        if not result:
            raise AIEmptyResponseError("Groq API returned an empty completion response.")
        return result

    def analyze_repository_metrics(
        self,
        repo_full_name: str,
        metrics: dict[str, Any],
    ) -> str:
        """Generates AI insights for repository commit velocity and health."""
        total_commits = metrics.get("total_commits", 0)
        active_contributors = metrics.get("active_contributors", 0)
        avg_pr_cycle = metrics.get("avg_pr_cycle_time_hours", 0.0)
        churn_rate = metrics.get("churn_rate", 0.0)
        lines_added = metrics.get("lines_added", 0)
        lines_deleted = metrics.get("lines_deleted", 0)

        system_prompt = (
            "You are GitPulse AI, an expert Principal Systems Engineer and Velocity Analyst. "
            "Analyze the given developer activity metrics and provide concise, high-value insights, "
            "bottlenecks, and recommended engineering workflow improvements. "
            "Never invent fictional commits or contributors. Ground your assessment strictly in the provided data."
        )

        is_empty_activity = total_commits == 0 and active_contributors == 0 and lines_added == 0

        if is_empty_activity:
            prompt = (
                f"Repository: {repo_full_name}\n"
                f"Metrics Data (30-day window):\n"
                f"- Total Commits (30d): 0\n"
                f"- Active Contributors: 0\n"
                f"- Average PR Cycle Time: 0.0 hours\n"
                f"- Code Churn Rate: 0.0%\n"
                f"- Lines Added: 0\n"
                f"- Lines Deleted: 0\n\n"
                "Assessment Note: The repository currently records zero commits or PRs within the analyzed 30-day window. "
                "Provide a structured assessment covering: "
                "1. Velocity Health: Acknowledge inactive or newly registered repository state. "
                "2. Review Bottlenecks: Note absence of active review pipelines. "
                "3. Strategic Action: Recommend verifying GitHub webhook connectivity, contributor branch setup, and commit cadence."
            )
        else:
            prompt = (
                f"Repository: {repo_full_name}\n"
                f"Metrics Data:\n"
                f"- Total Commits (30d): {total_commits}\n"
                f"- Active Contributors: {active_contributors}\n"
                f"- Average PR Cycle Time: {avg_pr_cycle:.1f} hours\n"
                f"- Code Churn Rate: {churn_rate * 100:.1f}%\n"
                f"- Lines Added: {lines_added}\n"
                f"- Lines Deleted: {lines_deleted}\n\n"
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
