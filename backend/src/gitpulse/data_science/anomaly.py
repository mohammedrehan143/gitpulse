"""Module B: Repository Anomaly Detection Engine for GitPulse."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class AnomalyDetector:
    """Robust multi-metric GitHub activity anomaly detector using rolling MAD and Isolation Forest."""

    def __init__(self, rolling_window_days: int = 14, default_threshold: float = 3.0):
        self.rolling_window_days = rolling_window_days
        self.default_threshold = default_threshold

    @staticmethod
    def compute_modified_z_score(
        observed: float,
        history: list[float] | np.ndarray,
        eps: float = 1e-4,
    ) -> tuple[float, float, float]:
        """Calculates robust modified z-score using Median Absolute Deviation (MAD).

        Returns: (modified_z_score, median, mad)
        """
        arr = np.array(history, dtype=float)
        if len(arr) == 0:
            return 0.0, 0.0, 0.0

        median = float(np.median(arr))
        mad = float(np.median(np.abs(arr - median)))

        # Zero-variance safe handling
        if mad < eps:
            # If historical variance is zero (e.g. all days had 0 commits),
            # small fluctuations should not trigger critical alarms.
            diff = abs(observed - median)
            if diff <= 2.0:
                return 0.0, median, 0.0
            # Scale deviation smoothly relative to scale
            smoothed_denom = max(1.0, median * 0.5)
            score = 0.6745 * diff / smoothed_denom
            return float(score), median, mad

        score = 0.6745 * abs(observed - median) / mad
        return float(score), median, mad

    def detect_univariate_anomalies(
        self,
        daily_records: dict[str, int],
        metric_name: str = "commits",
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Detects anomalous days using rolling historical window without future information leakage."""
        thresh = threshold or self.default_threshold
        if len(daily_records) < self.rolling_window_days + 1:
            return []

        sorted_dates = sorted(daily_records.keys())
        anomalies: list[dict[str, Any]] = []

        for idx in range(self.rolling_window_days, len(sorted_dates)):
            curr_date = sorted_dates[idx]
            observed_val = float(daily_records[curr_date])

            # Strictly past window [idx - W : idx] to eliminate future leakage
            prior_dates = sorted_dates[idx - self.rolling_window_days : idx]
            prior_vals = [float(daily_records[d]) for d in prior_dates]

            z_score, median_val, mad = self.compute_modified_z_score(observed_val, prior_vals)

            if z_score >= thresh:
                # Classify severity
                if z_score >= thresh * 2.0:
                    severity = "HIGH"
                elif z_score >= thresh * 1.4:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"

                direction = "surge" if observed_val > median_val else "drop"
                ratio = round(observed_val / max(median_val, 1.0), 1)

                explanation = (
                    f"Unusual {metric_name} {direction}: {int(observed_val)} observed "
                    f"vs {median_val:.1f} rolling median ({ratio}x change, score: {z_score:.2f})."
                )

                anomalies.append(
                    {
                        "date": curr_date,
                        "metric": metric_name,
                        "observed_value": observed_val,
                        "baseline_median": round(median_val, 2),
                        "mad": round(mad, 2),
                        "anomaly_score": round(z_score, 2),
                        "severity": severity,
                        "direction": direction,
                        "explanation": explanation,
                    }
                )

        return anomalies

    def detect_multivariate_anomalies(
        self,
        daily_metrics_df: pd.DataFrame,
        feature_cols: list[str] | None = None,
        contamination: float = 0.05,
    ) -> list[dict[str, Any]]:
        """Detects multidimensional anomalies across activity vectors using Isolation Forest."""
        cols = feature_cols or ["commits", "prs_opened", "issues_created", "contributors"]
        available_cols = [c for c in cols if c in daily_metrics_df.columns]

        if len(daily_metrics_df) < 20 or len(available_cols) < 2:
            return []

        clean_df = daily_metrics_df.sort_values("date").reset_index(drop=True)
        X = clean_df[available_cols].fillna(0.0).values

        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        preds = iso_forest.fit_predict(X)
        scores = -iso_forest.score_samples(X)  # Higher score = more anomalous

        anomalies: list[dict[str, Any]] = []
        threshold = float(np.percentile(scores, (1.0 - contamination) * 100))

        for idx, (pred, score) in enumerate(zip(preds, scores, strict=False)):
            if pred == -1 and score >= threshold:
                row = clean_df.iloc[idx]
                details = ", ".join(f"{col}: {int(row[col])}" for col in available_cols)
                anomalies.append(
                    {
                        "date": str(row["date"]),
                        "metric": "multivariate_activity",
                        "observed_value": round(float(score), 3),
                        "baseline_median": round(threshold, 3),
                        "anomaly_score": round(float(score * 10.0), 2),
                        "severity": "HIGH" if score > threshold * 1.2 else "MEDIUM",
                        "direction": "outlier",
                        "explanation": f"Multivariate outlier detected via Isolation Forest ({details}).",
                    }
                )

        return anomalies

    def analyze_repository(
        self,
        commits_series: dict[str, int],
        issues_series: dict[str, int] | None = None,
        prs_series: dict[str, int] | None = None,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        """Runs comprehensive univariate and multivariate anomaly diagnostics on repository timeline."""
        total_days = len(commits_series)
        if total_days < self.rolling_window_days + 1:
            return {
                "status": "INSUFFICIENT_HISTORY",
                "message": f"Need at least {self.rolling_window_days + 1} days for anomaly detection, got {total_days}.",
                "total_anomalies": 0,
                "anomalies": [],
            }

        detected: list[dict[str, Any]] = []

        # 1. Commit anomalies
        commit_anoms = self.detect_univariate_anomalies(
            commits_series, metric_name="commits", threshold=threshold
        )
        detected.extend(commit_anoms)

        # 2. PR anomalies if data available
        if prs_series and len(prs_series) >= self.rolling_window_days + 1:
            pr_anoms = self.detect_univariate_anomalies(
                prs_series, metric_name="prs_opened", threshold=threshold
            )
            detected.extend(pr_anoms)

        # 3. Issue anomalies if data available
        if issues_series and len(issues_series) >= self.rolling_window_days + 1:
            issue_anoms = self.detect_univariate_anomalies(
                issues_series, metric_name="issues_created", threshold=threshold
            )
            detected.extend(issue_anoms)

        # Sort chronologically descending
        detected.sort(key=lambda x: x["date"], reverse=True)

        return {
            "status": "ANALYZED",
            "threshold_used": threshold or self.default_threshold,
            "rolling_window_days": self.rolling_window_days,
            "total_days_evaluated": total_days,
            "total_anomalies": len(detected),
            "anomalies": detected,
        }
