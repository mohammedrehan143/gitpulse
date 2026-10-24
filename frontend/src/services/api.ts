import { VelocityResponse, EventsResponse } from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');

export async function fetchRepositoryVelocity(
  owner: string,
  repo: string,
  timeframe = '30d',
  granularity = 'day'
): Promise<VelocityResponse> {
  const url = `${API_BASE_URL}/repos/${owner}/${repo}/velocity?timeframe=${timeframe}&granularity=${granularity}`;
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
  const url = `${API_BASE_URL}/repos/${owner}/${repo}/events?limit=${limit}&offset=${offset}`;
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
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const wsUrl = `${protocol}//${host}/api/v1/ws/repos/${owner}/${repo}`;
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
