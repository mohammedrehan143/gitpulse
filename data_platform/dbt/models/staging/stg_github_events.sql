-- Staging model: Deduplicate and cast raw GitHub events

WITH raw_source AS (
    SELECT
        id AS internal_id,
        event_id,
        event_type,
        repo_id,
        actor_login,
        action,
        created_at AS event_timestamp,
        ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY created_at DESC) AS dedupe_rank
    FROM {{ source('gitpulse_raw', 'github_events') }}
)

SELECT
    event_id,
    event_type,
    repo_id,
    actor_login,
    action,
    event_timestamp,
    DATE(event_timestamp) AS event_date
FROM raw_source
WHERE dedupe_rank = 1
