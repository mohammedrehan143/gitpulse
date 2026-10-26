"""Tests for Module A (Activity Forecasting) and Module B (Anomaly Detection)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.src.gitpulse.data_science.anomaly import AnomalyDetector
from backend.src.gitpulse.data_science.forecasting import ActivityForecaster


def test_forecaster_prepare_daily_series():
    raw_counts = {
        "2026-10-01": 5,
        "2026-10-03": 10,  # 2026-10-02 missing
    }
    df = ActivityForecaster.prepare_daily_series(raw_counts)
    assert len(df) == 3
    assert list(df["count"]) == [5.0, 0.0, 10.0]
    assert df["is_weekend"].iloc[0] in (0.0, 1.0)


def test_forecaster_insufficient_history():
    forecaster = ActivityForecaster()
    raw_counts = {"2026-10-01": 2, "2026-10-02": 3}
    res = forecaster.generate_forecast(raw_counts, horizon_days=7)
    assert res["status"] == "INSUFFICIENT_HISTORY"
    assert res["forecast"] == []


def test_forecaster_generate_forecast():
    forecaster = ActivityForecaster()
    # 30 days of data with weekly cycle
    raw_counts = {}
    base_date = datetime(2026, 9, 1, tzinfo=UTC)
    for d in range(35):
        dt = base_date + timedelta(days=d)
        val = 15 if dt.weekday() < 5 else 2
        raw_counts[dt.strftime("%Y-%m-%d")] = val

    res = forecaster.generate_forecast(raw_counts, horizon_days=7)
    assert res["status"] == "SUCCESS"
    assert len(res["forecast"]) == 7
    assert res["evaluation"] is not None
    assert "ml_model_mae" in res["evaluation"]

    # Check uncertainty bounds
    for pt in res["forecast"]:
        assert pt["lower_bound"] <= pt["forecast"]
        assert pt["upper_bound"] >= pt["forecast"]
        assert pt["forecast"] >= 0.0


def test_anomaly_modified_z_score_zero_variance():
    # History with zero variance (all zeroes)
    score, median, mad = AnomalyDetector.compute_modified_z_score(1.0, [0.0] * 14)
    # Minor fluctuation should not trigger alarm
    assert score == 0.0
    assert mad == 0.0

    # Massive surge on zero history
    score_surge, _, _ = AnomalyDetector.compute_modified_z_score(50.0, [0.0] * 14)
    assert score_surge > 3.0


def test_anomaly_detector_temporal_safety_and_detection():
    detector = AnomalyDetector(rolling_window_days=7, default_threshold=3.0)
    # Normal days (10 each day), then day 15 spike (100)
    series = {}
    base_date = datetime(2026, 10, 1, tzinfo=UTC)
    for d in range(20):
        dt = base_date + timedelta(days=d)
        series[dt.strftime("%Y-%m-%d")] = 100 if d == 15 else 10

    results = detector.analyze_repository(series, threshold=3.0)
    assert results["status"] == "ANALYZED"
    anomalies = results["anomalies"]
    assert len(anomalies) >= 1

    spike_date = (base_date + timedelta(days=15)).strftime("%Y-%m-%d")
    spike_anoms = [a for a in anomalies if a["date"] == spike_date]
    assert len(spike_anoms) == 1
    assert spike_anoms[0]["observed_value"] == 100.0
    assert spike_anoms[0]["baseline_median"] == 10.0
    assert spike_anoms[0]["severity"] == "HIGH"
