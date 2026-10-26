"""Module A: Developer Activity Forecasting Engine for GitPulse."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error


class ActivityForecaster:
    """Production-grade daily repository activity forecasting with statistical baselines and ML models."""

    def __init__(self, history_window_days: int = 90, forecast_horizon_days: int = 7):
        self.history_window_days = history_window_days
        self.forecast_horizon_days = forecast_horizon_days

    @staticmethod
    def prepare_daily_series(
        raw_daily_counts: dict[str, int],
        target_end_date: datetime | None = None,
        fill_zero: bool = True,
    ) -> pd.DataFrame:
        """Converts date-keyed dictionaries into contiguous calendar-day series.

        Distinguishes missing data from true zero activity by completing the date range.
        """
        if not raw_daily_counts:
            return pd.DataFrame(columns=["date", "count", "day_of_week", "is_weekend"])

        parsed_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in raw_daily_counts.keys()]
        min_date = min(parsed_dates)
        max_date = target_end_date.date() if target_end_date else max(parsed_dates)

        if min_date > max_date:
            min_date = max_date

        all_dates = pd.date_range(start=min_date, end=max_date, freq="D")
        df = pd.DataFrame({"date": all_dates})
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")

        if fill_zero:
            df["count"] = df["date_str"].map(lambda d: float(raw_daily_counts.get(d, 0)))
        else:
            df["count"] = df["date_str"].map(
                lambda d: float(raw_daily_counts[d]) if d in raw_daily_counts else np.nan
            )

        df["day_of_week"] = df["date"].dt.dayofweek
        df["is_weekend"] = df["day_of_week"].apply(lambda x: 1.0 if x >= 5 else 0.0)
        return df

    @staticmethod
    def _create_lag_features(df: pd.DataFrame) -> pd.DataFrame:
        """Generates autoregressive lag and rolling window features strictly from past values."""
        feat_df = df.copy()
        for lag in [1, 2, 3, 7, 14]:
            feat_df[f"lag_{lag}"] = feat_df["count"].shift(lag)

        # Rolling 7-day statistics shifted by 1 to prevent target leakage
        feat_df["rolling_mean_7"] = (
            feat_df["count"].shift(1).rolling(window=7, min_periods=3).mean()
        )
        feat_df["rolling_std_7"] = (
            feat_df["count"].shift(1).rolling(window=7, min_periods=3).std().fillna(0.0)
        )
        return feat_df

    def evaluate_models(
        self,
        df: pd.DataFrame,
        holdout_days: int = 7,
    ) -> dict[str, Any]:
        """Performs chronological holdout evaluation comparing Baseline vs ML models."""
        n = len(df)
        if n < holdout_days + 14:
            return {
                "status": "INSUFFICIENT_HISTORY",
                "message": f"Need at least {holdout_days + 14} days of continuous history, got {n} days.",
            }

        train_df = df.iloc[:-holdout_days].copy()
        test_df = df.iloc[-holdout_days:].copy()
        y_true = test_df["count"].values

        # 1. Baseline: Seasonal Naive (7-day lag baseline)
        if len(train_df) >= 7:
            seasonal_naive_pred = train_df["count"].iloc[-7:].values
            if len(seasonal_naive_pred) == holdout_days:
                s_naive_mae = float(mean_absolute_error(y_true, seasonal_naive_pred))
            else:
                s_naive_mae = float(
                    mean_absolute_error(y_true, np.full(holdout_days, train_df["count"].mean()))
                )
        else:
            seasonal_naive_pred = np.full(holdout_days, train_df["count"].mean())
            s_naive_mae = float(mean_absolute_error(y_true, seasonal_naive_pred))

        # 2. Baseline: 7-day Moving Average
        ma_val = float(train_df["count"].tail(7).mean())
        ma_pred = np.full(holdout_days, ma_val)
        ma_mae = float(mean_absolute_error(y_true, ma_pred))

        # 3. Autoregressive ML Model (Ridge Regression with Lags)
        feat_df = self._create_lag_features(df)
        feature_cols = [
            "lag_1",
            "lag_2",
            "lag_3",
            "lag_7",
            "lag_14",
            "rolling_mean_7",
            "rolling_std_7",
            "day_of_week",
            "is_weekend",
        ]

        # Drop NaN rows resulting from 14-day lags
        clean_df = feat_df.dropna(subset=feature_cols).copy()
        train_clean = clean_df.iloc[:-holdout_days]
        test_clean = clean_df.iloc[-holdout_days:]

        if len(train_clean) >= 10 and len(test_clean) == holdout_days:
            X_tr, y_tr = train_clean[feature_cols].values, train_clean["count"].values
            X_te = test_clean[feature_cols].values

            model = Ridge(alpha=1.0)
            model.fit(X_tr, y_tr)
            ml_pred = np.clip(model.predict(X_te), a_min=0.0, a_max=None)
            ml_mae = float(mean_absolute_error(y_true, ml_pred))
            ml_rmse = float(math.sqrt(mean_squared_error(y_true, ml_pred)))
        else:
            ml_pred = ma_pred
            ml_mae = ma_mae
            ml_rmse = float(math.sqrt(mean_squared_error(y_true, ma_pred)))

        return {
            "status": "EVALUATED",
            "holdout_days": holdout_days,
            "sample_size": n,
            "metrics": {
                "seasonal_naive_mae": round(s_naive_mae, 2),
                "moving_average_mae": round(ma_mae, 2),
                "ml_model_mae": round(ml_mae, 2),
                "ml_model_rmse": round(ml_rmse, 2),
                "mae_improvement_pct": round(
                    max(0.0, ((s_naive_mae - ml_mae) / max(s_naive_mae, 0.01)) * 100), 1
                ),
            },
        }

    def generate_forecast(
        self,
        raw_daily_counts: dict[str, int],
        horizon_days: int = 7,
    ) -> dict[str, Any]:
        """Generates future activity forecast with prediction intervals and model diagnostics."""
        df = self.prepare_daily_series(raw_daily_counts)
        n = len(df)

        if n < 14:
            return {
                "status": "INSUFFICIENT_HISTORY",
                "message": f"Historical series contains only {n} days. Minimum required is 14 days for forecasting.",
                "forecast": [],
                "metrics": None,
            }

        # Run chronological holdout evaluation
        eval_result = self.evaluate_models(df, holdout_days=min(7, n // 3))

        # Train ML model on all available data with lag features
        feat_df = self._create_lag_features(df)
        feature_cols = [
            "lag_1",
            "lag_2",
            "lag_3",
            "lag_7",
            "lag_14",
            "rolling_mean_7",
            "rolling_std_7",
            "day_of_week",
            "is_weekend",
        ]
        clean_df = feat_df.dropna(subset=feature_cols)

        if len(clean_df) >= 7:
            X_all = clean_df[feature_cols].values
            y_all = clean_df["count"].values
            model = Ridge(alpha=1.0)
            model.fit(X_all, y_all)
            in_sample_preds = model.predict(X_all)
            residual_std = float(np.std(y_all - in_sample_preds))
        else:
            model = None
            residual_std = float(df["count"].std() or 1.0)

        # Multi-step autoregressive recursive forecast
        history_counts = list(df["count"].values)
        last_date = df["date"].iloc[-1]
        forecast_points = []

        for step in range(1, horizon_days + 1):
            future_date = last_date + timedelta(days=step)
            dow = future_date.dayofweek
            is_wknd = 1.0 if dow >= 5 else 0.0

            # Build feature vector from recent simulated history
            lag_1 = history_counts[-1]
            lag_2 = history_counts[-2] if len(history_counts) >= 2 else lag_1
            lag_3 = history_counts[-3] if len(history_counts) >= 3 else lag_2
            lag_7 = history_counts[-7] if len(history_counts) >= 7 else lag_1
            lag_14 = history_counts[-14] if len(history_counts) >= 14 else lag_7
            r_mean_7 = float(np.mean(history_counts[-7:]))
            r_std_7 = float(np.std(history_counts[-7:]))

            if model:
                x_vec = np.array(
                    [[lag_1, lag_2, lag_3, lag_7, lag_14, r_mean_7, r_std_7, dow, is_wknd]]
                )
                predicted_val = float(max(0.0, model.predict(x_vec)[0]))
            else:
                # Fallback to seasonal lag
                predicted_val = float(max(0.0, lag_7))

            # Uncertainty expands with forecast horizon
            uncertainty_margin = (1.96 * residual_std) * math.sqrt(1.0 + 0.15 * (step - 1))
            lower_bound = max(0.0, round(predicted_val - uncertainty_margin, 1))
            upper_bound = round(predicted_val + uncertainty_margin, 1)

            forecast_points.append(
                {
                    "date": future_date.strftime("%Y-%m-%d"),
                    "forecast": round(predicted_val, 1),
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "is_weekend": bool(is_wknd),
                }
            )
            history_counts.append(predicted_val)

        # Historical series tail for visual continuity in dashboard
        recent_history = [
            {"date": row["date_str"], "actual": int(row["count"])}
            for _, row in df.tail(30).iterrows()
        ]

        return {
            "status": "SUCCESS",
            "model_type": "RidgeAutoregressiveWithLags",
            "horizon_days": horizon_days,
            "history_days_analyzed": n,
            "forecast": forecast_points,
            "history": recent_history,
            "evaluation": eval_result.get("metrics"),
        }
