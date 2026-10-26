"""Tests for Module C (Issue Resolution Time) and Module D (PR Review Delay Analysis)."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from backend.src.gitpulse.data_science.issue_resolution import IssueResolutionPredictor
from backend.src.gitpulse.data_science.pr_review_delay import PRReviewDelayAnalyzer


@pytest.fixture
def temp_models_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def test_issue_resolution_insufficient_data(temp_models_dir):
    predictor = IssueResolutionPredictor(models_dir=temp_models_dir)
    res = predictor.train_and_evaluate([], repo_name="test/repo")
    assert res["status"] == "INSUFFICIENT_DATA"


def test_issue_resolution_training_and_prediction(temp_models_dir):
    predictor = IssueResolutionPredictor(models_dir=temp_models_dir)

    # Generate 25 synthetic resolved issues
    base_time = datetime(2026, 9, 1, tzinfo=UTC)
    issues = []
    for i in range(25):
        c_at = base_time + timedelta(days=i)
        duration = 10.0 + (i % 5) * 8.0
        cl_at = c_at + timedelta(hours=duration)
        issues.append(
            {
                "id": 1000 + i,
                "title": f"Issue #{i}: Fix database connection timeout",
                "body": "Detailed report with `stack trace`",
                "labels": ["bug", "backend"] if i % 2 == 0 else ["enhancement"],
                "created_at": c_at.isoformat(),
                "closed_at": cl_at.isoformat(),
            }
        )

    train_res = predictor.train_and_evaluate(issues, repo_name="test/repo")
    assert train_res["status"] == "TRAINED"
    assert "best_model" in train_res
    assert "baseline_metrics" in train_res
    assert train_res["baseline_metrics"]["median_hours"] > 0

    # Prediction on candidate issue
    pred_res = predictor.predict_resolution_time(
        {
            "title": "Bug in API authentication",
            "body": "User cannot login with valid token",
            "labels": ["bug"],
            "created_at": "2026-10-25T10:00:00Z",
        },
        repo_name="test/repo",
    )
    assert pred_res["status"] == "SUCCESS"
    assert pred_res["predicted_duration_hours"] > 0
    assert pred_res["upper_bound_hours"] >= pred_res["predicted_duration_hours"]


def test_pr_review_delay_censoring_and_correlations(temp_models_dir):
    analyzer = PRReviewDelayAnalyzer(models_dir=temp_models_dir)

    base_time = datetime(2026, 9, 1, tzinfo=UTC)
    prs = []
    for i in range(25):
        c_at = base_time + timedelta(days=i)
        # 80% reviewed, 20% unreviewed
        is_reviewed = i % 5 != 0
        r_at = (c_at + timedelta(hours=5.0 + i * 2.0)) if is_reviewed else None

        prs.append(
            {
                "id": 2000 + i,
                "title": f"PR #{i}: Add feature",
                "body": "PR description",
                "additions": 20 + i * 15,
                "deletions": 5 + i * 3,
                "changed_files": 2 + i // 4,
                "created_at": c_at.isoformat(),
                "first_reviewed_at": r_at.isoformat() if r_at else None,
            }
        )

    # Correlation analysis
    stats_res = analyzer.compute_statistical_correlations(prs)
    assert stats_res["status"] == "ANALYZED"
    assert stats_res["censoring_stats"]["unreviewed_censored_prs"] == 5
    assert stats_res["censoring_stats"]["censoring_rate_pct"] == 20.0
    assert len(stats_res["size_brackets"]) == 4

    # Model training
    train_res = analyzer.train_and_evaluate(prs, repo_name="test/repo")
    assert train_res["status"] == "TRAINED"
    assert "HistGradientBoosting" in train_res["candidate_models"]

    # Prediction
    pred_res = analyzer.predict_review_delay(
        {
            "title": "Add analytics caching layer",
            "body": "Performance optimization for big queries",
            "additions": 150,
            "deletions": 30,
            "changed_files": 4,
            "created_at": "2026-10-25T14:00:00Z",
        },
        repo_name="test/repo",
    )
    assert pred_res["status"] == "SUCCESS"
    assert pred_res["predicted_delay_hours"] > 0
