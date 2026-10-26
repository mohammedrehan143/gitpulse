# GitPulse Domain Interface Contracts

## 1. Overview
This document serves as the binding contractual agreement between the Backend and Frontend domain engineering squads. Changes to these contracts require explicit approval from the `software-architect` and `master-orchestrator`.

---

## 2. API Contract: Repository Analytics & Velocity Metrics

### 2.1 GET `/api/v1/repos/{owner}/{repo}/velocity`
Retrieves aggregated commit velocity and PR turnaround metrics over a given timeframe.

**Query Parameters:**
- `timeframe` (optional, string, default: `"30d"`): Allowed values: `"7d"`, `"14d"`, `"30d"`, `"90d"`, `"1y"`.
- `granularity` (optional, string, default: `"day"`): Allowed values: `"hour"`, `"day"`, `"week"`.

**Success Response (200 OK):**
```json
{
  "repository": {
    "id": 1029384,
    "owner": "apache",
    "name": "spark",
    "full_name": "apache/spark"
  },
  "timeframe": "30d",
  "granularity": "day",
  "summary": {
    "total_commits": 342,
    "active_contributors": 48,
    "avg_pr_cycle_time_hours": 18.5,
    "lines_added": 14250,
    "lines_deleted": 8920,
    "churn_rate": 0.38
  },
  "timeline": [
    {
      "timestamp": "2026-10-01T00:00:00Z",
      "commit_count": 14,
      "pr_opened_count": 6,
      "pr_merged_count": 5,
      "active_authors": 8,
      "net_lines": 450
    }
  ]
}
```

**Error Responses:**
- `400 Bad Request`: `{"error": "INVALID_TIMEFRAME", "message": "Invalid timeframe parameter"}`
- `404 Not Found`: `{"error": "REPO_NOT_FOUND", "message": "Repository not tracked"}`
- `429 Too Many Requests`: `{"error": "RATE_LIMITED", "retry_after_seconds": 60}`

---

### 2.2 GET `/api/v1/repos/{owner}/{repo}/events`
Paginated stream of raw or enriched GitHub activity events.

**Query Parameters:**
- `limit` (integer, default: 20, max: 100)
- `offset` (integer, default: 0)
- `event_type` (optional string): `"PushEvent"`, `"PullRequestEvent"`, `"IssuesEvent"`, `"PullRequestReviewEvent"`

**Success Response (200 OK):**
```json
{
  "total_count": 1420,
  "limit": 20,
  "offset": 0,
  "events": [
    {
      "event_id": "evt_9872134",
      "event_type": "PullRequestEvent",
      "actor": "octocat",
      "actor_avatar_url": "https://avatars.githubusercontent.com/u/583231",
      "action": "opened",
      "payload_summary": "PR #124: Add PySpark structured streaming sink",
      "created_at": "2026-10-24T18:45:10Z"
    }
  ]
}
```

---

## 3. Streaming Event Contract (Kafka Topic: `gitpulse.github.raw_events`)

**Key:** `string` (Repository full name, e.g. `"apache/spark"`)

**Value (JSON Schema):**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RawGitHubEvent",
  "type": "object",
  "required": ["event_id", "event_type", "repo_id", "actor_login", "timestamp", "payload"],
  "properties": {
    "event_id": { "type": "string" },
    "event_type": { "type": "string" },
    "repo_id": { "type": "integer" },
    "repo_name": { "type": "string" },
    "actor_login": { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload": { "type": "object" }
  }
}
```

---

## 4. Real-time WebSocket Contract (`/api/v1/ws/repos/{owner}/{repo}`)
- Client connects via `ws://<host>:<port>/api/v1/ws/repos/{owner}/{repo}`
- Client sends subscribe: `{"action": "subscribe", "events": ["metrics_update", "new_event"]}`
- Server emits real-time event notifications:
```json
{
  "type": "event_stream",
  "event": {
    "event_id": "evt_9872135",
    "event_type": "PushEvent",
    "actor": "dev-alice",
    "timestamp": "2026-10-24T19:02:15Z"
  }
}
```

---

## 5. Data Science Intelligence Contracts

### 5.1 GET `/api/v1/intelligence/{owner}/{repo}/forecasting`
Retrieves daily developer activity forecasts with 95% uncertainty intervals and baseline comparison.

**Query Parameters:**
- `horizon` (optional, integer, default: `7`, max: `30`): Forecast horizon in days.

**Success Response (200 OK):**
```json
{
  "status": "SUCCESS",
  "model_type": "RidgeAutoregressiveWithLags",
  "horizon_days": 7,
  "history_days_analyzed": 35,
  "forecast": [
    {
      "date": "2026-10-27",
      "forecast": 14.2,
      "lower_bound": 10.1,
      "upper_bound": 18.3,
      "is_weekend": false
    }
  ],
  "history": [
    { "date": "2026-10-26", "actual": 15 }
  ],
  "evaluation": {
    "seasonal_naive_mae": 3.8,
    "moving_average_mae": 4.1,
    "ml_model_mae": 2.6,
    "ml_model_rmse": 3.1,
    "mae_improvement_pct": 31.6
  }
}
```

### 5.2 GET `/api/v1/intelligence/{owner}/{repo}/anomalies`
Surfaces anomalous spikes and drops via rolling MAD and Isolation Forest without future leakage.

**Query Parameters:**
- `threshold` (optional, float, default: `3.0`, min: `1.0`, max: `10.0`): Modified z-score sensitivity.

**Success Response (200 OK):**
```json
{
  "status": "ANALYZED",
  "threshold_used": 3.0,
  "rolling_window_days": 14,
  "total_days_evaluated": 35,
  "total_anomalies": 1,
  "anomalies": [
    {
      "date": "2026-10-20",
      "metric": "commits",
      "observed_value": 68.0,
      "baseline_median": 12.0,
      "anomaly_score": 4.82,
      "severity": "HIGH",
      "direction": "surge",
      "explanation": "Unusual commits surge: 68 observed vs 12.0 rolling median (5.7x change, score: 4.82)."
    }
  ]
}
```

### 5.3 POST `/api/v1/intelligence/{owner}/{repo}/issue-resolution/predict`
Estimates resolution turnaround in hours for a candidate issue.

**Request Payload:**
```json
{
  "title": "Fix database connection leak under heavy concurrency",
  "body": "Detailed stacktrace and pool timeout reproduction",
  "labels": ["bug", "backend"]
}
```

**Success Response (200 OK):**
```json
{
  "status": "SUCCESS",
  "predicted_duration_hours": 18.4,
  "lower_bound_hours": 10.2,
  "upper_bound_hours": 26.6,
  "confidence_tier": "HIGH (Trained ML Ensemble)",
  "model_version": "0.2.0",
  "best_model": "HistGradientBoosting"
}
```

### 5.4 POST `/api/v1/intelligence/{owner}/{repo}/pr-review-delay/predict`
Estimates first-review turnaround in hours for an inbound PR.

**Request Payload:**
```json
{
  "title": "feat: Add high-throughput streaming Kafka connector",
  "additions": 450,
  "deletions": 50,
  "changed_files": 8
}
```

**Success Response (200 OK):**
```json
{
  "status": "SUCCESS",
  "predicted_delay_hours": 8.5,
  "lower_bound_hours": 2.5,
  "upper_bound_hours": 14.5,
  "confidence_tier": "HIGH (Trained ML Ensemble)",
  "model_version": "0.2.0",
  "best_model": "HistGradientBoosting"
}
```

