import {
  KeepAliveResponse,
  VelocityResponse,
  EventsResponse,
  RepositoriesResponse,
  RefreshRepositoriesResponse,
  AIInsightsResponse,
  ActivityForecastResponse,
  AnomalyResponse,
  IssueResolutionInsights,
  IssuePredictRequest,
  IssuePredictResponse,
  PRReviewDelayInsights,
  PRReviewPredictRequest,
  PRReviewPredictResponse,
  RepoStatsResponse,
  PullRequestsResponse,
  IssuesResponse,
  ContributorsResponse,
  SyncRepositoryResponse,
  ReconciliationResponse,
  RepositoryAIOverviewResponse,
  PRIntelligenceResponse,
  DeveloperIntelligenceResponse,
  TeamReportResponse,
  AIAssistantChatResponse,
} from '../types';

export function getApiBaseUrl(): string {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/$/, '');
  if (!envUrl) {
    return '/api/v1';
  }
  if (!envUrl.endsWith('/api/v1')) {
    return `${envUrl}/api/v1`;
  }
  return envUrl;
}

export function getWsBaseUrl(owner: string, repo: string): string {
  const envWsUrl = (import.meta.env.VITE_WS_BASE_URL || '').trim().replace(/\/$/, '');
  if (envWsUrl) {
    let base = envWsUrl;
    if (!base.endsWith('/ws')) {
      base = base.endsWith('/api/v1') ? `${base}/ws` : `${base}/api/v1/ws`;
    }
    return `${base}/repos/${owner}/${repo}`;
  }

  const apiBase = getApiBaseUrl();
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    const wsPrefix = apiBase.startsWith('https://') ? 'wss://' : 'ws://';
    const cleanHostPath = apiBase.replace(/^https?:\/\//, '');
    return `${wsPrefix}${cleanHostPath}/ws/repos/${owner}/${repo}`;
  }

  if (typeof window !== 'undefined' && window.location) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/v1/ws/repos/${owner}/${repo}`;
  }

  return `ws://127.0.0.1:8000/api/v1/ws/repos/${owner}/${repo}`;
}

export async function fetchDiscoveredRepositories(): Promise<RepositoriesResponse> {
  const url = `${getApiBaseUrl()}/repos`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch repositories: ${res.statusText}`);
  }
  return res.json();
}

export async function refreshDiscoveredRepositories(): Promise<RefreshRepositoriesResponse> {
  const url = `${getApiBaseUrl()}/repos/refresh`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) {
    throw new Error(`Failed to refresh repositories: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRepositoryVelocity(
  owner: string,
  repo: string,
  timeframe = '30d',
  granularity = 'day'
): Promise<VelocityResponse> {
  const url = `${getApiBaseUrl()}/repos/${owner}/${repo}/velocity?timeframe=${timeframe}&granularity=${granularity}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch velocity metrics: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRepositoryEvents(
  owner: string,
  repo: string,
  limit = 20,
  offset = 0
): Promise<EventsResponse> {
  const url = `${getApiBaseUrl()}/repos/${owner}/${repo}/events?limit=${limit}&offset=${offset}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch events: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchAIInsights(
  owner: string,
  repo: string
): Promise<AIInsightsResponse> {
  const url = `${getApiBaseUrl()}/repos/${owner}/${repo}/ai-insights`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) {
    throw new Error(`Failed to generate AI insights: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRepositoryStats(
  owner: string,
  repo: string
): Promise<RepoStatsResponse> {
  const url = `${getApiBaseUrl()}/repos/${owner}/${repo}/stats`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch repository stats: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRepositoryPullRequests(
  owner: string,
  repo: string,
  state = 'all',
  limit = 20,
  offset = 0
): Promise<PullRequestsResponse> {
  const url = `${getApiBaseUrl()}/repos/${owner}/${repo}/pulls?state=${state}&limit=${limit}&offset=${offset}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch pull requests: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRepositoryIssues(
  owner: string,
  repo: string,
  state = 'all',
  limit = 20,
  offset = 0
): Promise<IssuesResponse> {
  const url = `${getApiBaseUrl()}/repos/${owner}/${repo}/issues?state=${state}&limit=${limit}&offset=${offset}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch issues: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRepositoryContributors(
  owner: string,
  repo: string
): Promise<ContributorsResponse> {
  const url = `${getApiBaseUrl()}/repos/${owner}/${repo}/contributors`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch contributors: ${res.statusText}`);
  }
  return res.json();
}

export async function syncRepository(
  owner: string,
  repo: string,
  incremental = true
): Promise<SyncRepositoryResponse> {
  const url = `${getApiBaseUrl()}/repos/${owner}/${repo}/sync?incremental=${incremental}`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) {
    throw new Error(`Failed to trigger repository sync: ${res.statusText}`);
  }
  return res.json();
}

export async function reconcileRepository(
  owner: string,
  repo: string
): Promise<ReconciliationResponse> {
  const url = `${getApiBaseUrl()}/repos/${owner}/${repo}/reconcile`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) {
    throw new Error(`Failed to reconcile repository: ${res.statusText}`);
  }
  return res.json();
}

export function createRepoWebSocket(
  owner: string,
  repo: string,
  onMessage: (data: unknown) => void,
  onError?: (err: Event) => void
): WebSocket | null {
  if (typeof window === 'undefined' || !window.WebSocket) {
    return null;
  }
  const wsUrl = getWsBaseUrl(owner, repo);
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    ws.send(JSON.stringify({ action: 'subscribe', events: ['metrics_update', 'new_event'] }));
  };

  ws.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      onMessage(parsed);
    } catch {
      // Ignore unparseable frames
    }
  };

  if (onError) {
    ws.onerror = onError;
  }

  return ws;
}

// -------------------------------------------------------------
// Data Science Intelligence API Services
// -------------------------------------------------------------

export async function fetchActivityForecast(
  owner: string,
  repo: string,
  horizon = 7
): Promise<ActivityForecastResponse> {
  const url = `${getApiBaseUrl()}/intelligence/${owner}/${repo}/forecasting?horizon=${horizon}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch activity forecast: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchAnomalies(
  owner: string,
  repo: string,
  threshold = 3.0
): Promise<AnomalyResponse> {
  const url = `${getApiBaseUrl()}/intelligence/${owner}/${repo}/anomalies?threshold=${threshold}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch activity anomalies: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchIssueResolutionInsights(
  owner: string,
  repo: string
): Promise<IssueResolutionInsights> {
  const url = `${getApiBaseUrl()}/intelligence/${owner}/${repo}/issue-resolution`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch issue resolution insights: ${res.statusText}`);
  }
  return res.json();
}

export async function predictIssueResolution(
  owner: string,
  repo: string,
  data: IssuePredictRequest
): Promise<IssuePredictResponse> {
  const url = `${getApiBaseUrl()}/intelligence/${owner}/${repo}/issue-resolution/predict`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to predict issue resolution: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchPRReviewDelayInsights(
  owner: string,
  repo: string
): Promise<PRReviewDelayInsights> {
  const url = `${getApiBaseUrl()}/intelligence/${owner}/${repo}/pr-review-delay`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch PR review delay insights: ${res.statusText}`);
  }
  return res.json();
}

export async function predictPRReviewDelay(
  owner: string,
  repo: string,
  data: PRReviewPredictRequest
): Promise<PRReviewPredictResponse> {
  const url = `${getApiBaseUrl()}/intelligence/${owner}/${repo}/pr-review-delay/predict`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`Failed to predict PR review delay: ${res.statusText}`);
  }
  return res.json();
}

export async function triggerModelTraining(
  owner: string,
  repo: string
): Promise<{ status?: string; repository?: string }> {
  const url = `${getApiBaseUrl()}/intelligence/${owner}/${repo}/train`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) {
    throw new Error(`Failed to trigger model training: ${res.statusText}`);
  }
  return res.json();
}


export async function sendKeepAlivePulse(triggerSync = false): Promise<KeepAliveResponse> {
  const url = `${getApiBaseUrl()}/keepalive?source=web_client_heartbeat&sync=${triggerSync}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Keep-alive pulse request failed: ${res.statusText}`);
  }
  return res.json();
}


export async function fetchRepositoryAIOverview(
  owner: string,
  repo: string,
  timeframe = '30d',
  refresh = false
): Promise<RepositoryAIOverviewResponse> {
  const url = `${getApiBaseUrl()}/ai/repos/${owner}/${repo}/overview?timeframe=${timeframe}&refresh=${refresh}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch AI repository overview: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchPRIntelligence(
  owner: string,
  repo: string,
  prNumber: number,
  refresh = false
): Promise<PRIntelligenceResponse> {
  const url = `${getApiBaseUrl()}/ai/repos/${owner}/${repo}/prs/${prNumber}?refresh=${refresh}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch PR intelligence: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDeveloperIntelligence(
  owner: string,
  repo: string,
  developer: string,
  refresh = false
): Promise<DeveloperIntelligenceResponse> {
  const url = `${getApiBaseUrl()}/ai/repos/${owner}/${repo}/developers/${developer}?refresh=${refresh}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch developer intelligence: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTeamAIReport(
  owner: string,
  repo: string,
  timeframe = '7d',
  refresh = false
): Promise<TeamReportResponse> {
  const url = `${getApiBaseUrl()}/ai/repos/${owner}/${repo}/team-report?timeframe=${timeframe}&refresh=${refresh}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch team AI report: ${res.statusText}`);
  }
  return res.json();
}

export async function askAIEngineeringAssistant(
  question: string,
  targetRepo?: string
): Promise<AIAssistantChatResponse> {
  const url = `${getApiBaseUrl()}/ai/assistant/chat`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, target_repo: targetRepo || null }),
  });
  if (!res.ok) {
    throw new Error(`Failed to query AI assistant: ${res.statusText}`);
  }
  return res.json();
}
