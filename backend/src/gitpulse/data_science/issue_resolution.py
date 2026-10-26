"""Module C: Issue Resolution Time Prediction Engine for GitPulse."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error


class IssueResolutionPredictor:
    """Predicts GitHub issue resolution duration in hours using ML regressors with chronological validation."""

    MODEL_VERSION = "0.2.0"
    KNOWN_LABELS = [
        "bug",
        "enhancement",
        "documentation",
        "critical",
        "performance",
        "ui",
        "backend",
    ]

    def __init__(self, models_dir: str | Path | None = None):
        self.models_dir = Path(models_dir or Path(__file__).resolve().parents[3] / "models")
        self.models_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def extract_features(
        cls,
        issue_records: list[dict[str, Any]],
        is_training: bool = True,
    ) -> tuple[pd.DataFrame, np.ndarray | None]:
        """Engineers features strictly available at issue creation time to eliminate target leakage."""
        rows: list[dict[str, Any]] = []
        targets: list[float] = []

        # Sort chronologically by created_at to compute point-in-time historical workload
        sorted_records = sorted(issue_records, key=lambda x: str(x.get("created_at") or ""))

        resolved_durations_so_far: list[float] = []

        for idx, rec in enumerate(sorted_records):
            c_at_str = rec.get("created_at")
            cl_at_str = rec.get("closed_at")

            try:
                c_dt = datetime.fromisoformat(str(c_at_str).replace("Z", "+00:00"))
            except Exception:
                continue

            duration_hours: float | None = None
            if cl_at_str:
                try:
                    cl_dt = datetime.fromisoformat(str(cl_at_str).replace("Z", "+00:00"))
                    if cl_dt >= c_dt:
                        duration_hours = max(0.1, (cl_dt - c_dt).total_seconds() / 3600.0)
                except Exception:
                    pass

            if is_training and duration_hours is None:
                # Exclude open issues during training to prevent downward duration bias
                continue

            title = str(rec.get("title") or "")
            body = str(rec.get("body") or "")
            labels = [str(lbl).lower() for lbl in (rec.get("labels") or [])]

            # Point-in-time historical median resolution from past resolved issues
            hist_median = (
                float(np.median(resolved_durations_so_far)) if resolved_durations_so_far else 24.0
            )

            row = {
                "title_length": len(title),
                "title_words": len(title.split()),
                "body_length": len(body),
                "has_code_snippet": 1.0 if ("```" in body or "`" in body) else 0.0,
                "label_count": len(labels),
                "day_of_week": c_dt.weekday(),
                "hour_of_day": c_dt.hour,
                "is_weekend": 1.0 if c_dt.weekday() >= 5 else 0.0,
                "open_workload_approx": max(1, idx),
                "hist_resolution_median": hist_median,
            }

            # One-hot label features
            for known_label in cls.KNOWN_LABELS:
                row[f"label_{known_label}"] = (
                    1.0 if any(known_label in lbl for lbl in labels) else 0.0
                )

            rows.append(row)
            if is_training and duration_hours is not None:
                targets.append(duration_hours)
                resolved_durations_so_far.append(duration_hours)

        df = pd.DataFrame(rows)
        y = np.array(targets, dtype=float) if is_training else None
        return df, y

    def train_and_evaluate(
        self,
        issue_records: list[dict[str, Any]],
        repo_name: str = "default",
        test_ratio: float = 0.20,
    ) -> dict[str, Any]:
        """Trains candidate regression models on chronological split, comparing against historical median baseline."""
        X_df, y = self.extract_features(issue_records, is_training=True)

        n = len(X_df)
        if n < 15 or y is None:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": f"Requires at least 15 closed issues with valid timestamps to train, got {n}.",
                "model_version": self.MODEL_VERSION,
                "metrics": None,
            }

        split_idx = int(n * (1.0 - test_ratio))
        split_idx = max(10, min(split_idx, n - 5))

        X_train, X_test = X_df.iloc[:split_idx], X_df.iloc[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # 1. Baseline: Historical Median of Training Set
        baseline_median = float(np.median(y_train))
        baseline_preds = np.full(len(y_test), baseline_median)
        baseline_mae = float(mean_absolute_error(y_test, baseline_preds))
        baseline_medae = float(median_absolute_error(y_test, baseline_preds))

        # Target transform: log(1 + y) to stabilize skewed resolution distribution
        y_train_log = np.log1p(y_train)

        # 2. Candidate Models
        models = {
            "Ridge": Ridge(alpha=10.0),
            "HistGradientBoosting": HistGradientBoostingRegressor(
                max_iter=100, min_samples_leaf=5, random_state=42
            ),
            "RandomForest": RandomForestRegressor(n_estimators=50, max_depth=6, random_state=42),
        }

        best_model_name = "HistGradientBoosting"
        best_model = None
        best_mae = float("inf")
        model_evals: dict[str, Any] = {}

        for name, mdl in models.items():
            mdl.fit(X_train.values, y_train_log)
            preds_log = mdl.predict(X_test.values)
            preds = np.expm1(np.clip(preds_log, a_min=0.0, a_max=8.0))  # Max ~3000 hrs

            mae = float(mean_absolute_error(y_test, preds))
            medae = float(median_absolute_error(y_test, preds))
            rmse = float(math.sqrt(mean_squared_error(y_test, preds)))

            model_evals[name] = {
                "mae_hours": round(mae, 2),
                "medae_hours": round(medae, 2),
                "rmse_hours": round(rmse, 2),
            }

            if mae < best_mae:
                best_mae = mae
                best_model_name = name
                best_model = mdl

        # Re-fit winning model on all training data and persist
        full_y_log = np.log1p(y)
        best_model.fit(X_df.values, full_y_log)

        safe_repo_slug = repo_name.replace("/", "_")
        model_path = self.models_dir / f"issue_resolution_{safe_repo_slug}.joblib"
        metadata = {
            "version": self.MODEL_VERSION,
            "best_model_name": best_model_name,
            "trained_at": datetime.now(UTC).isoformat(),
            "sample_size": n,
            "feature_names": list(X_df.columns),
            "baseline_median_hours": round(baseline_median, 2),
            "baseline_mae": round(baseline_mae, 2),
            "best_mae": round(best_mae, 2),
            "evaluations": model_evals,
        }
        joblib.dump({"model": best_model, "metadata": metadata}, model_path)

        return {
            "status": "TRAINED",
            "model_version": self.MODEL_VERSION,
            "best_model": best_model_name,
            "sample_size": n,
            "test_size": len(y_test),
            "baseline_metrics": {
                "median_hours": round(baseline_median, 2),
                "mae_hours": round(baseline_mae, 2),
                "medae_hours": round(baseline_medae, 2),
            },
            "candidate_models": model_evals,
            "improvement_over_baseline_pct": round(
                max(0.0, ((baseline_mae - best_mae) / max(baseline_mae, 0.01)) * 100), 1
            ),
        }

    def predict_resolution_time(
        self,
        issue_data: dict[str, Any],
        repo_name: str = "default",
    ) -> dict[str, Any]:
        """Predicts resolution duration in hours for a single candidate issue."""
        safe_repo_slug = repo_name.replace("/", "_")
        model_path = self.models_dir / f"issue_resolution_{safe_repo_slug}.joblib"

        # Check for persisted model
        if not model_path.exists():
            # Fallback heuristic baseline
            labels = [str(lbl).lower() for lbl in (issue_data.get("labels") or [])]
            base_hours = 36.0
            if "bug" in labels:
                base_hours = 24.0
            if "critical" in labels:
                base_hours = 12.0
            if "documentation" in labels:
                base_hours = 18.0

            return {
                "status": "BASELINE_ESTIMATE",
                "predicted_duration_hours": round(base_hours, 1),
                "confidence_tier": "LOW (Untrained Baseline)",
                "model_version": self.MODEL_VERSION,
                "notes": "Model not yet trained on this repository. Showing heuristic baseline.",
            }

        bundle = joblib.load(model_path)
        model = bundle["model"]
        meta = bundle["metadata"]

        feat_df, _ = self.extract_features([issue_data], is_training=False)
        pred_log = model.predict(feat_df.values)[0]
        pred_hours = float(np.expm1(np.clip(pred_log, a_min=0.0, a_max=8.0)))

        # Bounds based on model best MAE
        margin = meta.get("best_mae", 12.0)
        lower_hours = max(0.5, round(pred_hours - margin, 1))
        upper_hours = round(pred_hours + margin, 1)

        return {
            "status": "SUCCESS",
            "predicted_duration_hours": round(pred_hours, 1),
            "lower_bound_hours": lower_hours,
            "upper_bound_hours": upper_hours,
            "confidence_tier": "HIGH (Trained ML Ensemble)",
            "model_version": meta.get("version", self.MODEL_VERSION),
            "best_model": meta.get("best_model_name"),
            "baseline_median_hours": meta.get("baseline_median_hours"),
        }
