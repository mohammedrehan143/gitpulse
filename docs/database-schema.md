# GitPulse Database Schema (PostgreSQL)

## Entity Relationship Overview

```text
┌──────────────────────┐         1:N         ┌──────────────────────┐
│     repositories     ├────────────────────►│    github_events     │
└──────────┬───────────┘                     └──────────────────────┘
           │
           │ 1:N                             1:N
           ├────────────────────────────────►┌──────────────────────┐
           │                                 │       commits        │
           │                                 └──────────────────────┘
           │ 1:N
           └────────────────────────────────►┌──────────────────────┐
                                             │  developer_metrics   │
                                             └──────────────────────┘
```

## Tables

### 1. `repositories`
- `id`: BIGSERIAL PRIMARY KEY
- `github_id`: BIGINT UNIQUE NOT NULL
- `owner`: VARCHAR(100) NOT NULL
- `name`: VARCHAR(100) NOT NULL
- `full_name`: VARCHAR(200) UNIQUE NOT NULL
- `stars_count`: INT DEFAULT 0
- `forks_count`: INT DEFAULT 0
- `created_at`: TIMESTAMPTZ DEFAULT NOW()

### 2. `github_events`
- `id`: BIGSERIAL PRIMARY KEY
- `event_id`: VARCHAR(64) UNIQUE NOT NULL
- `event_type`: VARCHAR(64) NOT NULL
- `repo_id`: BIGINT NOT NULL REFERENCES repositories(id)
- `actor_login`: VARCHAR(100) NOT NULL
- `actor_avatar_url`: VARCHAR(255)
- `action`: VARCHAR(50)
- `payload_summary`: VARCHAR(500)
- `raw_payload`: JSONB DEFAULT '{}'
- `created_at`: TIMESTAMPTZ NOT NULL

### 3. `commits`
- `id`: BIGSERIAL PRIMARY KEY
- `sha`: VARCHAR(64) UNIQUE NOT NULL
- `repo_id`: BIGINT NOT NULL REFERENCES repositories(id)
- `author_name`: VARCHAR(100) NOT NULL
- `author_email`: VARCHAR(150) NOT NULL
- `message`: VARCHAR(1000) NOT NULL
- `lines_added`: INT DEFAULT 0
- `lines_deleted`: INT DEFAULT 0
- `committed_at`: TIMESTAMPTZ NOT NULL

### 4. `developer_metrics`
- `id`: BIGSERIAL PRIMARY KEY
- `repo_id`: BIGINT NOT NULL REFERENCES repositories(id)
- `metric_date`: VARCHAR(10) NOT NULL
- `commit_count`: INT DEFAULT 0
- `active_contributors`: INT DEFAULT 0
- `avg_pr_cycle_time_hours`: DOUBLE PRECISION DEFAULT 0.0
- `lines_added`: INT DEFAULT 0
- `lines_deleted`: INT DEFAULT 0
- `churn_rate`: DOUBLE PRECISION DEFAULT 0.0
- UNIQUE(repo_id, metric_date)
