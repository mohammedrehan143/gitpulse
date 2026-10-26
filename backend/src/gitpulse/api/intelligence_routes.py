"""FastAPI Endpoints for GitPulse Data Science Intelligence Platform."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.src.gitpulse.services.intelligence_service import IntelligenceService

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])
intelligence_service = IntelligenceService()


# ---------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------
class ForecastPoint(BaseModel):
    date: str
    forecast: float
    lower_bound: float
    upper_bound: float
    is_weekend: bool


class ActivityForecastResponse(BaseModel):
    status: str
    model_type: str | None = None
    horizon_days: int
    history_days_analyzed: int
    forecast: list[ForecastPoint] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)
    evaluation: dict[str, Any] | None = None
    message: str | None = None


class AnomalyItem(BaseModel):
    date: str
    metric: str
    observed_value: float
    baseline_median: float
    anomaly_score: float
    severity: str
    direction: str
    explanation: str


class AnomalyResponse(BaseModel):
    status: str
    threshold_used: float
    rolling_window_days: int
    total_days_evaluated: int
    total_anomalies: int
    anomalies: list[AnomalyItem] = Field(default_factory=list)
    message: str | None = None


class IssuePredictRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    body: str = Field(default="", max_length=5000)
    labels: list[str] = Field(default_factory=list)


class IssuePredictResponse(BaseModel):
    status: str
    predicted_duration_hours: float
    lower_bound_hours: float | None = None
    upper_bound_hours: float | None = None
    confidence_tier: str
    model_version: str
    best_model: str | None = None
    baseline_median_hours: float | None = None
    notes: str | None = None


class PRReviewPredictRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    changed_files: int = Field(default=1, ge=1)


class PRReviewPredictResponse(BaseModel):
    status: str
    predicted_delay_hours: float
    lower_bound_hours: float | None = None
    upper_bound_hours: float | None = None
    confidence_tier: str
    model_version: str
    best_model: str | None = None
    baseline_median_hours: float | None = None
    notes: str | None = None


# ---------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------
@router.get("/{owner}/{repo}/forecasting", response_model=ActivityForecastResponse)
async def get_forecasting(
    owner: str,
    repo: str,
    horizon: int = Query(default=7, ge=1, le=30),
) -> ActivityForecastResponse:
    """Forecasts repository activity across the next 7 or 14 days with uncertainty intervals."""
    try:
        data = await intelligence_service.get_activity_forecast(owner, repo, horizon_days=horizon)
        return ActivityForecastResponse(
            status=data.get("status", "SUCCESS"),
            model_type=data.get("model_type"),
            horizon_days=data.get("horizon_days", horizon),
            history_days_analyzed=data.get("history_days_analyzed", 0),
            forecast=[ForecastPoint(**p) for p in data.get("forecast", [])],
            history=data.get("history", []),
            evaluation=data.get("evaluation"),
            message=data.get("message"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecasting error for {owner}/{repo}: {exc}",
        ) from exc


@router.get("/{owner}/{repo}/anomalies", response_model=AnomalyResponse)
async def get_anomalies(
    owner: str,
    repo: str,
    threshold: float = Query(default=3.0, ge=1.0, le=10.0),
) -> AnomalyResponse:
    """Surfaces anomalous spikes or drops in daily commits, PRs, and issues."""
    try:
        data = await intelligence_service.get_anomalies(owner, repo, threshold=threshold)
        return AnomalyResponse(
            status=data.get("status", "ANALYZED"),
            threshold_used=data.get("threshold_used", threshold),
            rolling_window_days=data.get("rolling_window_days", 14),
            total_days_evaluated=data.get("total_days_evaluated", 0),
            total_anomalies=data.get("total_anomalies", 0),
            anomalies=[AnomalyItem(**a) for a in data.get("anomalies", [])],
            message=data.get("message"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection error for {owner}/{repo}: {exc}",
        ) from exc


@router.get("/{owner}/{repo}/issue-resolution")
async def get_issue_resolution_insights(owner: str, repo: str) -> dict[str, Any]:
    """Retrieves issue resolution model evaluations, historical turnaround baseline, and training state."""
    try:
        return await intelligence_service.get_issue_resolution_insights(owner, repo)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Issue resolution insights error for {owner}/{repo}: {exc}",
        ) from exc


@router.post("/{owner}/{repo}/issue-resolution/predict", response_model=IssuePredictResponse)
async def predict_issue_resolution(
    owner: str,
    repo: str,
    request: IssuePredictRequest,
) -> IssuePredictResponse:
    """Predicts estimated resolution hours for a candidate issue based on historical patterns."""
    try:
        res = await intelligence_service.predict_issue_resolution(owner, repo, request.model_dump())
        return IssuePredictResponse(**res)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Issue prediction error: {exc}",
        ) from exc


@router.get("/{owner}/{repo}/pr-review-delay")
async def get_pr_review_delay_insights(owner: str, repo: str) -> dict[str, Any]:
    """Returns PR turnaround factor correlations, size-bracket breakdown, and regression evaluations."""
    try:
        return await intelligence_service.get_pr_review_delay_insights(owner, repo)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PR review delay insights error: {exc}",
        ) from exc


@router.post("/{owner}/{repo}/pr-review-delay/predict", response_model=PRReviewPredictResponse)
async def predict_pr_review_delay(
    owner: str,
    repo: str,
    request: PRReviewPredictRequest,
) -> PRReviewPredictResponse:
    """Predicts first-review delay in hours for an incoming pull request."""
    try:
        res = await intelligence_service.predict_pr_review_delay(owner, repo, request.model_dump())
        return PRReviewPredictResponse(**res)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PR review delay prediction error: {exc}",
        ) from exc


@router.post("/{owner}/{repo}/train")
async def train_all_models(owner: str, repo: str) -> dict[str, Any]:
    """Triggers complete model training and persistence for all analytical modules."""
    try:
        return await intelligence_service.train_all_models(owner, repo)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training error: {exc}",
        ) from exc
