"""Unit tests for Groq AI Orchestration Service."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.src.gitpulse.services.ai_service import GroqAIService


class MockDelta:
    def __init__(self, content: str | None):
        self.content = content


class MockChoice:
    def __init__(self, content: str | None):
        self.delta = MockDelta(content)


class MockChunk:
    def __init__(self, content: str | None):
        self.choices = [MockChoice(content)]


def test_groq_ai_service_streaming(monkeypatch):
    """Verifies that GroqAIService properly streams delta chunks."""
    service = GroqAIService(api_key="gsk_mockKey123", model="openai/gpt-oss-120b")

    mock_chunks = [
        MockChunk("Hello"),
        MockChunk(" from"),
        MockChunk(" Groq"),
        MockChunk("!"),
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = iter(mock_chunks)
    monkeypatch.setattr(service, "_client", mock_client)

    stream = list(service.stream_completion(prompt="Hello"))
    assert stream == ["Hello", " from", " Groq", "!"]

    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "openai/gpt-oss-120b"
    assert call_kwargs["stream"] is True
    assert call_kwargs["temperature"] == 1.0
    assert call_kwargs["max_completion_tokens"] == 2048
    assert call_kwargs["reasoning_effort"] == "medium"


def test_groq_ai_service_generate_completion(monkeypatch):
    """Verifies aggregation of tokens into a single completion string."""
    service = GroqAIService(api_key="gsk_mockKey123")

    mock_chunks = [
        MockChunk("Commit"),
        MockChunk(" velocity"),
        MockChunk(" is healthy."),
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = iter(mock_chunks)
    monkeypatch.setattr(service, "_client", mock_client)

    full_text = service.generate_completion(prompt="Analyze metrics")
    assert full_text == "Commit velocity is healthy."


def test_groq_ai_service_analyze_repository_metrics(monkeypatch):
    """Verifies repository metrics prompt compilation and analysis generation."""
    service = GroqAIService(api_key="gsk_mockKey123")

    mock_chunks = [MockChunk("Velocity assessment completed.")]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = iter(mock_chunks)
    monkeypatch.setattr(service, "_client", mock_client)

    insights = service.analyze_repository_metrics(
        repo_full_name="apache/spark",
        metrics={
            "total_commits": 142,
            "active_contributors": 12,
            "avg_pr_cycle_time_hours": 14.5,
            "churn_rate": 0.18,
            "lines_added": 4500,
            "lines_deleted": 810,
        },
    )
    assert insights == "Velocity assessment completed."

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    user_message = next(m["content"] for m in call_kwargs["messages"] if m["role"] == "user")
    assert "apache/spark" in user_message
    assert "142" in user_message
    assert "18.0%" in user_message
