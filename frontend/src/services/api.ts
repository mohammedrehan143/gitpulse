import { VelocityResponse, EventsResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

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
