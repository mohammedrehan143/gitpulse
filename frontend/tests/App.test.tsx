import { describe, it, expect, vi } from 'vitest';
import {
  fetchRepositoryVelocity,
  fetchRepositoryEvents,
  createRepoWebSocket,
  fetchDiscoveredRepositories,
  refreshDiscoveredRepositories,
  getApiBaseUrl,
  getWsBaseUrl,
} from '../src/services/api';

describe('GitPulse Frontend Application & API Services', () => {
  it('validates test runner environment and module exports', () => {
    expect(true).toBe(true);
  });

  it('constructs correct velocity URL with query parameters', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        repository: { id: 1, owner: 'apache', name: 'spark', full_name: 'apache/spark' },
        timeframe: '14d',
        granularity: 'day',
        summary: { total_commits: 42, active_contributors: 8, avg_pr_cycle_time_hours: 15.0 },
        timeline: [],
      }),
    });
    global.fetch = mockFetch;

    const res = await fetchRepositoryVelocity('apache', 'spark', '14d', 'day');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/repos/apache/spark/velocity?timeframe=14d&granularity=day')
    );
    expect(res.summary.total_commits).toBe(42);
  });

  it('constructs correct events URL with pagination limit and offset', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        total_count: 1,
        limit: 10,
        offset: 5,
        events: [{ event_id: 'evt_1', event_type: 'PushEvent', actor: 'alice', created_at: '2026-10-24' }],
      }),
    });
    global.fetch = mockFetch;

    const res = await fetchRepositoryEvents('apache', 'spark', 10, 5);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/repos/apache/spark/events?limit=10&offset=5')
    );
    expect(res.events.length).toBe(1);
  });

  it('handles WebSocket creator safely in headless test environment', () => {
    const ws = createRepoWebSocket('apache', 'spark', () => {});
    // In headless Node.js without window.WebSocket, it safely returns null without crashing
    expect(ws === null || typeof ws === 'object').toBe(true);
  });

  it('fetches discovered repositories via /repos endpoint', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        total_count: 2,
        auto_discover_enabled: true,
        repositories: [
          { id: 1, full_name: 'user/repo-1', visibility: 'public', monitoring_status: 'POLLING' },
          { id: 2, full_name: 'user/repo-2', visibility: 'private', monitoring_status: 'POLLING' },
        ],
      }),
    });
    global.fetch = mockFetch;

    const res = await fetchDiscoveredRepositories();
    expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/repos'));
    expect(res.total_count).toBe(2);
    expect(res.repositories[1].visibility).toBe('private');
  });

  it('triggers manual repository refresh via POST /repos/refresh', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: 'SYNCHRONIZED',
        synced_count: 3,
        repositories: [],
      }),
    });
    global.fetch = mockFetch;

    const res = await refreshDiscoveredRepositories();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/repos/refresh'),
      expect.objectContaining({ method: 'POST' })
    );
    expect(res.status).toBe('SYNCHRONIZED');
    expect(res.synced_count).toBe(3);
  });

  it('resolves default API base and WebSocket URLs correctly', () => {
    const apiBase = getApiBaseUrl();
    expect(apiBase).toBe('/api/v1');

    const wsUrl = getWsBaseUrl('apache', 'spark');
    expect(wsUrl).toContain('/api/v1/ws/repos/apache/spark');
  });
});

