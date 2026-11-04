-- =============================================================================
-- Migration 001: Initial Relational Schema for GitPulse
-- =============================================================================

CREATE TABLE IF NOT EXISTS repositories (
    id BIGSERIAL PRIMARY KEY,
    github_id BIGINT UNIQUE NOT NULL,
    owner VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    full_name VARCHAR(200) UNIQUE NOT NULL,
    stars_count INT DEFAULT 0,
    forks_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_repos_owner ON repositories(owner);
CREATE INDEX idx_repos_name ON repositories(name);

CREATE TABLE IF NOT EXISTS github_events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    repo_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    actor_login VARCHAR(100) NOT NULL,
    actor_avatar_url VARCHAR(255),
    action VARCHAR(50),
    payload_summary VARCHAR(500),
    raw_payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_repo_created ON github_events(repo_id, created_at DESC);
CREATE INDEX idx_events_type ON github_events(event_type);
CREATE INDEX idx_events_actor ON github_events(actor_login);

CREATE TABLE IF NOT EXISTS commits (
    id BIGSERIAL PRIMARY KEY,
    sha VARCHAR(64) UNIQUE NOT NULL,
    repo_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    author_name VARCHAR(100) NOT NULL,
    author_email VARCHAR(150) NOT NULL,
    message VARCHAR(1000) NOT NULL,
    lines_added INT DEFAULT 0,
    lines_deleted INT DEFAULT 0,
    committed_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_commits_repo_time ON commits(repo_id, committed_at DESC);

CREATE TABLE IF NOT EXISTS developer_metrics (
    id BIGSERIAL PRIMARY KEY,
    repo_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    metric_date VARCHAR(10) NOT NULL,
    commit_count INT DEFAULT 0,
    active_contributors INT DEFAULT 0,
    avg_pr_cycle_time_hours DOUBLE PRECISION DEFAULT 0.0,
    lines_added INT DEFAULT 0,
    lines_deleted INT DEFAULT 0,
    churn_rate DOUBLE PRECISION DEFAULT 0.0,
    CONSTRAINT uq_repo_metric_date UNIQUE (repo_id, metric_date)
);

CREATE INDEX idx_metrics_date ON developer_metrics(metric_date);

CREATE TABLE IF NOT EXISTS repository_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    repo_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    repo_github_id BIGINT NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    webhook_url VARCHAR(500),
    event_types JSONB DEFAULT '["push", "all"]'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_repo_active ON repository_subscriptions(repo_id, is_active);
CREATE INDEX idx_subscriptions_user ON repository_subscriptions(user_id);
CREATE INDEX idx_subscriptions_github_id ON repository_subscriptions(repo_github_id);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id BIGSERIAL PRIMARY KEY,
    delivery_id VARCHAR(128) UNIQUE NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    repo_github_id BIGINT,
    repo_full_name VARCHAR(200),
    payload_hash VARCHAR(64) NOT NULL,
    sender_login VARCHAR(100),
    status VARCHAR(30) DEFAULT 'PROCESSED',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_deliveries_delivery_id ON webhook_deliveries(delivery_id);
CREATE INDEX idx_deliveries_payload_hash ON webhook_deliveries(payload_hash);
