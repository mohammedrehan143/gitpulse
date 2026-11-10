-- =============================================================================
-- Migration 002: Production Readiness Schemas & Observability Checkpoints
-- Adds Pull Requests, Issues, Reviews, Checkpoints, Contributors & Indexes
-- =============================================================================

CREATE TABLE IF NOT EXISTS pull_requests (
    id BIGSERIAL PRIMARY KEY,
    repo_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    github_id BIGINT UNIQUE NOT NULL,
    number INT NOT NULL,
    title VARCHAR(500) NOT NULL,
    body VARCHAR(5000),
    state VARCHAR(20) DEFAULT 'open',
    author_login VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    merged_at TIMESTAMPTZ,
    first_reviewed_at TIMESTAMPTZ,
    additions INT DEFAULT 0,
    deletions INT DEFAULT 0,
    changed_files INT DEFAULT 0,
    review_comments_count INT DEFAULT 0,
    raw_payload JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_prs_repo_created ON pull_requests(repo_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prs_repo_state ON pull_requests(repo_id, state);
CREATE INDEX IF NOT EXISTS idx_prs_author ON pull_requests(author_login);

CREATE TABLE IF NOT EXISTS reviews (
    id BIGSERIAL PRIMARY KEY,
    pr_id BIGINT NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
    github_id BIGINT UNIQUE NOT NULL,
    reviewer_login VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    body VARCHAR(2000)
);

CREATE INDEX IF NOT EXISTS idx_reviews_pr_submitted ON reviews(pr_id, submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewer ON reviews(reviewer_login);

CREATE TABLE IF NOT EXISTS issues (
    id BIGSERIAL PRIMARY KEY,
    repo_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    github_id BIGINT UNIQUE NOT NULL,
    number INT NOT NULL,
    title VARCHAR(500) NOT NULL,
    body VARCHAR(5000),
    state VARCHAR(20) DEFAULT 'open',
    author_login VARCHAR(100) NOT NULL,
    labels JSONB DEFAULT '[]'::jsonb,
    comments_count INT DEFAULT 0,
    reopened_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    raw_payload JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_issues_repo_created ON issues(repo_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_issues_repo_state ON issues(repo_id, state);
CREATE INDEX IF NOT EXISTS idx_issues_author ON issues(author_login);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    target_repo VARCHAR(200) NOT NULL,
    status VARCHAR(30) DEFAULT 'RUNNING',
    records_processed INT DEFAULT 0,
    records_failed INT DEFAULT 0,
    error_message VARCHAR(1000),
    metadata_json JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_repo_status ON pipeline_runs(target_repo, status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started ON pipeline_runs(started_at DESC);

CREATE TABLE IF NOT EXISTS sync_checkpoints (
    id BIGSERIAL PRIMARY KEY,
    repo_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL,
    last_checkpoint_timestamp TIMESTAMPTZ,
    last_item_id VARCHAR(128),
    cursor VARCHAR(255),
    status VARCHAR(30) DEFAULT 'COMPLETED',
    error_message VARCHAR(1000),
    records_synced INT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_sync_checkpoint_repo_resource UNIQUE (repo_id, resource_type)
);

CREATE INDEX IF NOT EXISTS idx_sync_checkpoints_repo ON sync_checkpoints(repo_id, resource_type);

CREATE TABLE IF NOT EXISTS contributors (
    id BIGSERIAL PRIMARY KEY,
    repo_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    login VARCHAR(100) NOT NULL,
    name VARCHAR(150),
    email VARCHAR(200),
    avatar_url VARCHAR(255),
    html_url VARCHAR(255),
    contributions_count INT DEFAULT 0,
    commits_count INT DEFAULT 0,
    prs_count INT DEFAULT 0,
    issues_count INT DEFAULT 0,
    first_contributed_at TIMESTAMPTZ,
    last_contributed_at TIMESTAMPTZ,
    CONSTRAINT uq_contributors_repo_login UNIQUE (repo_id, login)
);

CREATE INDEX IF NOT EXISTS idx_contributors_repo_count ON contributors(repo_id, contributions_count DESC);
