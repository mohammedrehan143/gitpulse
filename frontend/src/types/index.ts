export interface RepositoryRef {
  id: number;
  owner: string;
  name: string;
  full_name: string;
}

export interface VelocitySummary {
  total_commits: number;
  active_contributors: number;
  avg_pr_cycle_time_hours: number;
  lines_added: number;
  lines_deleted: number;
  churn_rate: number;
}

export interface TimelinePoint {
  timestamp: string;
  commit_count: number;
  pr_opened_count: number;
  pr_merged_count: number;
  active_authors: number;
  net_lines: number;
}

export interface VelocityResponse {
  repository: RepositoryRef;
  timeframe: string;
  granularity: string;
  summary: VelocitySummary;
  timeline: TimelinePoint[];
}

export interface EventItem {
  event_id: string;
  event_type: string;
  actor: string;
  actor_avatar_url?: string;
  action?: string;
  payload_summary?: string;
  created_at: string;
}

export interface EventsResponse {
  total_count: number;
  limit: number;
  offset: number;
  events: EventItem[];
}
