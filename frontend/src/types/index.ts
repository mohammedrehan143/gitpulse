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

// Data Science Intelligence Types
export interface ForecastPoint {
  date: string;
  forecast: number;
  lower_bound: number;
  upper_bound: number;
  is_weekend: boolean;
}

export interface ActivityForecastResponse {
  status: string;
  model_type?: string;
  horizon_days: number;
  history_days_analyzed: number;
  forecast: ForecastPoint[];
  history: Array<{ date: string; actual: number }>;
  evaluation?: {
    seasonal_naive_mae: number;
    moving_average_mae: number;
    ml_model_mae: number;
    ml_model_rmse: number;
    mae_improvement_pct: number;
  };
  message?: string;
}

export interface AnomalyItem {
  date: string;
  metric: string;
  observed_value: number;
  baseline_median: number;
  anomaly_score: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  direction: 'surge' | 'drop' | 'outlier';
  explanation: string;
}

export interface AnomalyResponse {
  status: string;
  threshold_used: number;
  rolling_window_days: number;
  total_days_evaluated: number;
  total_anomalies: number;
  anomalies: AnomalyItem[];
  message?: string;
}

export interface IssuePredictRequest {
  title: string;
  body?: string;
  labels?: string[];
}

export interface IssuePredictResponse {
  status: string;
  predicted_duration_hours: number;
  lower_bound_hours?: number;
  upper_bound_hours?: number;
  confidence_tier: string;
  model_version: string;
  best_model?: string;
  baseline_median_hours?: number;
  notes?: string;
}

export interface IssueResolutionInsights {
  status: string;
  model_version?: string;
  best_model?: string;
  sample_size?: number;
  test_size?: number;
  baseline_metrics?: {
    median_hours: number;
    mae_hours: number;
    medae_hours: number;
  };
  candidate_models?: Record<string, { mae_hours: number; medae_hours: number; rmse_hours: number }>;
  improvement_over_baseline_pct?: number;
  message?: string;
}

export interface PRReviewPredictRequest {
  title: string;
  additions?: number;
  deletions?: number;
  changed_files?: number;
}

export interface PRReviewPredictResponse {
  status: string;
  predicted_delay_hours: number;
  lower_bound_hours?: number;
  upper_bound_hours?: number;
  confidence_tier: string;
  model_version: string;
  best_model?: string;
  baseline_median_hours?: number;
  notes?: string;
}

export interface PRReviewDelayInsights {
  statistics?: {
    status: string;
    censoring_stats?: {
      total_prs_analyzed: number;
      reviewed_prs: number;
      unreviewed_censored_prs: number;
      censoring_rate_pct: number;
    };
    correlations?: Record<string, {
      spearman_correlation: number;
      p_value: number;
      statistically_significant: boolean;
    }>;
    size_brackets?: Array<{
      bracket: string;
      count: number;
      median_delay_hours: number;
    }>;
    overall_median_delay_hours?: number;
    message?: string;
  };
  training?: {
    status: string;
    best_model?: string;
    sample_size?: number;
    baseline_metrics?: {
      median_hours: number;
      mae_hours: number;
      medae_hours: number;
    };
    candidate_models?: Record<string, { mae_hours: number; medae_hours: number; rmse_hours: number }>;
    improvement_over_baseline_pct?: number;
    message?: string;
  };
}


