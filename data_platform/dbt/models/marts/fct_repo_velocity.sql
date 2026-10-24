-- Fact model: Daily Repository Commit & PR Velocity

WITH daily_events AS (
    SELECT
        repo_id,
        event_date,
        COUNT(CASE WHEN event_type = 'PushEvent' THEN 1 END) AS total_commits,
        COUNT(CASE WHEN event_type = 'PullRequestEvent' AND action = 'opened' THEN 1 END) AS prs_opened,
        COUNT(CASE WHEN event_type = 'PullRequestEvent' AND action = 'closed' THEN 1 END) AS prs_merged,
        COUNT(DISTINCT actor_login) AS active_contributors
    FROM {{ ref('stg_github_events') }}
    GROUP BY repo_id, event_date
)

SELECT
    repo_id,
    event_date,
    total_commits,
    prs_opened,
    prs_merged,
    active_contributors,
    ROUND(CAST(total_commits AS NUMERIC) / NULLIF(active_contributors, 0), 2) AS commits_per_contributor
FROM daily_events
