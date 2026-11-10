"""FastAPI Endpoints for Groq-Powered AI Engineering Intelligence."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.src.gitpulse.common.logging import logger
from backend.src.gitpulse.services.groq_intelligence_service import groq_intelligence_service

router = APIRouter(prefix="/api/v1/ai", tags=["ai-intelligence"])


class AssistantChatRequest(BaseModel):
    """Payload for natural-language questions asked to the AI Engineering Assistant."""

    question: str = Field(
        ..., description="Natural-language question about repositories, PRs, or developers"
    )
    target_repo: str | None = Field(
        None, description="Optional target repository in 'owner/repo' format"
    )


def _parse_timeframe_days(timeframe: str) -> int:
    """Parses timeframe string (e.g., '7d', '30d', '90d') into integer days."""
    t = timeframe.strip().lower()
    if t.endswith("d"):
        try:
            return int(t[:-1])
        except ValueError:
            pass
    return 30


@router.get("/repos/{owner}/{repo}/overview")
async def get_repository_ai_overview(
    owner: str,
    repo: str,
    timeframe: str = Query("30d", description="Timeframe window, e.g., '7d', '30d'"),
    refresh: bool = Query(False, description="Bypass cache and force regenerate analysis"),
) -> dict[str, Any]:
    """Generates grounded repository health, activity, and cadence intelligence."""
    days = _parse_timeframe_days(timeframe)
    result = await groq_intelligence_service.generate_repository_intelligence(
        owner=owner,
        repo=repo,
        timeframe_days=days,
        force_refresh=refresh,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/repos/{owner}/{repo}/prs/{pr_number}")
async def get_pr_ai_intelligence(
    owner: str,
    repo: str,
    pr_number: int,
    refresh: bool = Query(False, description="Bypass cache and force regenerate analysis"),
) -> dict[str, Any]:
    """Generates pull request complexity, review risk, and activity intelligence."""
    result = await groq_intelligence_service.generate_pr_intelligence(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        force_refresh=refresh,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/repos/{owner}/{repo}/developers/{developer_login}")
async def get_developer_ai_intelligence(
    owner: str,
    repo: str,
    developer_login: str,
    refresh: bool = Query(False, description="Bypass cache and force regenerate analysis"),
) -> dict[str, Any]:
    """Generates evidence-based developer contribution summaries without misleading scores."""
    result = await groq_intelligence_service.generate_developer_intelligence(
        owner=owner,
        repo=repo,
        developer_login=developer_login,
        force_refresh=refresh,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/repos/{owner}/{repo}/team-report")
async def get_team_ai_report(
    owner: str,
    repo: str,
    timeframe: str = Query("7d", description="Timeframe window, e.g., '7d', '14d'"),
    refresh: bool = Query(False, description="Bypass cache and force regenerate report"),
) -> dict[str, Any]:
    """Generates weekly team engineering reports, distribution, and bottleneck analysis."""
    days = _parse_timeframe_days(timeframe)
    result = await groq_intelligence_service.generate_team_intelligence(
        owner=owner,
        repo=repo,
        timeframe_days=days,
        force_refresh=refresh,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/assistant/chat")
async def chat_with_engineering_assistant(
    request: AssistantChatRequest,
) -> dict[str, Any]:
    """Answers natural-language engineering questions strictly grounded in GitPulse database facts."""
    try:
        return await groq_intelligence_service.query_engineering_assistant(
            question=request.question,
            target_repo=request.target_repo,
        )
    except Exception as exc:
        logger.error("Error executing engineering assistant query: %s", exc)
        raise HTTPException(status_code=500, detail=f"Assistant query failure: {exc}") from exc
