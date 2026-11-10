export interface KeepAliveResponse {
  status: string;
  timestamp: string;
  database: string;
  repositories_count: number;
  events_count: number;
  last_synced_at: string | null;
  uptime_seconds: number;
  keep_alive_pulse: boolean;
  source: string;
  message: string;
}

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

export interface SyncCheckpointItem {
  resource_type: string;
  status: string;
  last_item_id?: string | null;
  last_checkpoint_timestamp?: string | null;
  records_synced: number;
}

export interface RepoStatsResponse {
  repository: string;
  total_commits: number;
  open_pull_requests: number;
  merged_pull_requests: number;
  closed_pull_requests: number;
  open_issues: number;
  closed_issues: number;
  total_contributors: number;
  avg_pr_cycle_time_hours: number;
  total_lines_added: number;
  total_lines_deleted: number;
  churn_rate: number;
  last_synced_at?: string | null;
  monitoring_status: string;
  checkpoints: SyncCheckpointItem[];
}

export interface PullRequestItem {
  id: number;
  github_id: number;
  number: number;
  title: string;
  state: string;
  author_login: string;
  created_at: string;
  updated_at?: string | null;
  closed_at?: string | null;
  merged_at?: string | null;
  first_reviewed_at?: string | null;
  additions: number;
  deletions: number;
  changed_files: number;
  review_comments_count: number;
}

export interface PullRequestsResponse {
  repository: string;
  total_count: number;
  limit: number;
  offset: number;
  pull_requests: PullRequestItem[];
}

export interface IssueItem {
  id: number;
  github_id: number;
  number: number;
  title: string;
  state: string;
  author_login: string;
  labels: string[];
  comments_count: number;
  created_at: string;
  updated_at?: string | null;
  closed_at?: string | null;
}

export interface IssuesResponse {
  repository: string;
  total_count: number;
  limit: number;
  offset: number;
  issues: IssueItem[];
}

export interface ContributorItem {
  id: number;
  login: string;
  name?: string | null;
  avatar_url?: string | null;
  html_url?: string | null;
  contributions_count: number;
  commits_count: number;
  prs_count: number;
  issues_count: number;
  first_contributed_at?: string | null;
  last_contributed_at?: string | null;
}

export interface ContributorsResponse {
  repository: string;
  total_count: number;
  contributors: ContributorItem[];
}

export interface SyncRepositoryResponse {
  status: string;
  pipeline_run_id?: number | null;
  target_repo: string;
  records_processed: number;
  records_failed: number;
  duration_seconds: number;
  error_message?: string | null;
}

export interface ReconciliationResponse {
  repository: string;
  status: string;
  reconciled_at: string;
  commits: Record<string, unknown>;
  pull_requests: Record<string, unknown>;
  issues: Record<string, unknown>;
  contributors: Record<string, unknown>;
  reviews: Record<string, unknown>;
  metrics_recalculated: boolean;
}

// -----------------------------------------------------------------------------
// Groq AI Engineering Intelligence Types
// -----------------------------------------------------------------------------

export interface RepositoryAIOverviewResponse {
  repository: string;
  timeframe_days: number;
  data_freshness: string;
  source: string;
  verified_facts: {
    total_commits: number;
    active_authors_count: number;
    lines_added: number;
    lines_deleted: number;
    code_churn_rate: number;
    inactive_days: number;
    open_prs_count: number;
    merged_prs_count: number;
    closed_prs_count: number;
    avg_pr_cycle_time_hours: number;
    long_running_prs_count: number;
    open_issues_count: number;
    closed_issues_count: number;
    tracked_contributors_count: number;
  };
  health_summary: string;
  activity_analysis: string;
  inactive_periods_detected: string;
  unusual_patterns: string[];
  recent_progress_summary: string;
  strategic_recommendations: string[];
  ai_interpretations: string[];
  missing_or_unavailable: string[];
  cached: boolean;
}

export interface PRIntelligenceResponse {
  repository: string;
  number: number;
  title: string;
  state: string;
  author: string;
  source: string;
  verified_metrics: {
    additions: number;
    deletions: number;
    total_changes: number;
    changed_files: number;
    review_comments_count: number;
    reviews_count: number;
  };
  pr_summary: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  risk_factors: string[];
  review_activity_analysis: string;
  long_running_flag: boolean;
  recommendations: string[];
  ai_interpretations: string[];
  missing_or_unavailable: string[];
  cached: boolean;
}

export interface DeveloperIntelligenceResponse {
  repository: string;
  developer: string;
  source: string;
  verified_metrics: {
    total_contributions: number;
    commits_count: number;
    prs_authored_count: number;
    prs_merged_count: number;
    lines_added: number;
    lines_deleted: number;
    first_active: string | null;
    last_active: string | null;
  };
  contribution_summary: string;
  commit_and_pr_patterns: string;
  contribution_trends: string;
  evidence_notes: string[];
  ai_interpretations: string[];
  missing_or_unavailable: string[];
  cached: boolean;
}

export interface TeamReportResponse {
  repository: string;
  timeframe_days: number;
  data_freshness: string;
  source: string;
  weekly_report: string;
  contribution_distribution_analysis: string;
  review_bottlenecks: string[];
  collaboration_patterns: string;
  team_recommendations: string[];
  ai_interpretations: string[];
  missing_or_unavailable: string[];
  cached: boolean;
}

export interface AIAssistantChatResponse {
  question: string;
  target_repo: string | null;
  source: string;
  answer: string;
  verified_facts: Record<string, unknown>;
  calculated_metrics: Record<string, unknown>;
  ai_interpretations: string[];
  missing_or_unavailable: string[];
  timeframe: string;
  data_freshness: string;
}



