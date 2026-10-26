import { VelocityResponse, EventsResponse, RepositoriesResponse, RefreshRepositoriesResponse } from '../types';

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

  return `ws://localhost:8000/api/v1/ws/repos/${owner}/${repo}`;
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
