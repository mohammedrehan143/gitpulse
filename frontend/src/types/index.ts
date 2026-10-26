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

export interface DiscoveredRepository {
  id: number;
  github_id: number;
  owner: string;
  name: string;
  full_name: string;
  description: string | null;
  visibility: string;
  default_branch: string;
  html_url: string | null;
  pushed_at: string | null;
  created_at: string | null;
  is_active: boolean;
  monitoring_status: string;
  last_synced_at: string | null;
  stars_count: number;
  forks_count: number;
}

export interface RepositoriesResponse {
  total_count: number;
  auto_discover_enabled: boolean;
  repositories: DiscoveredRepository[];
}

export interface RefreshRepositoriesResponse {
  status: string;
  synced_count: number;
  repositories: DiscoveredRepository[];
}

export interface AIInsightsResponse {
  repository: string;
  model: string;
  insights: string;
}

