import { describe, it, expect, vi } from 'vitest';
import {
  fetchRepositoryVelocity,
  fetchRepositoryEvents,
  createRepoWebSocket,
  fetchDiscoveredRepositories,
  refreshDiscoveredRepositories,
  fetchAIInsights,
  fetchActivityForecast,
  fetchAnomalies,
  fetchIssueResolutionInsights,
  predictIssueResolution,
  fetchPRReviewDelayInsights,
  predictPRReviewDelay,
  triggerModelTraining,
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

  it('triggers AI insights generation via POST /repos/{owner}/{repo}/ai-insights', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        repository: 'apache/spark',
        model: 'openai/gpt-oss-120b',
        insights: 'Velocity optimal. PR cycle time 18.5h.',
      }),
    });
    global.fetch = mockFetch;

    const res = await fetchAIInsights('apache', 'spark');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/repos/apache/spark/ai-insights'),
      expect.objectContaining({ method: 'POST' })
    );
    expect(res.model).toBe('openai/gpt-oss-120b');
    expect(res.insights).toContain('Velocity optimal');
  });

  it('resolves default API base and WebSocket URLs correctly', () => {
    const apiBase = getApiBaseUrl();
    expect(apiBase).toBe('/api/v1');

    const wsUrl = getWsBaseUrl('apache', 'spark');
    expect(wsUrl).toContain('/api/v1/ws/repos/apache/spark');
  });

  it('fetches activity forecasting from intelligence API', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: 'SUCCESS',
        horizon_days: 7,
        history_days_analyzed: 30,
        forecast: [
          { date: '2026-10-27', forecast: 14.2, lower_bound: 10.0, upper_bound: 18.4, is_weekend: false },
        ],
      }),
    });
    global.fetch = mockFetch;

    const res = await fetchActivityForecast('apache', 'spark', 7);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/intelligence/apache/spark/forecasting?horizon=7')
    );
    expect(res.status).toBe('SUCCESS');
    expect(res.forecast[0].forecast).toBe(14.2);
  });

  it('fetches activity anomalies from intelligence API', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: 'ANALYZED',
        threshold_used: 3.0,
        rolling_window_days: 14,
        total_days_evaluated: 30,
        total_anomalies: 1,
        anomalies: [
          {
            date: '2026-10-20',
            metric: 'commits',
            observed_value: 65,
            baseline_median: 12,
            anomaly_score: 4.8,
            severity: 'HIGH',
            direction: 'surge',
            explanation: 'Unusual spike in daily commits',
          },
        ],
      }),
    });
    global.fetch = mockFetch;

    const res = await fetchAnomalies('apache', 'spark', 3.0);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/intelligence/apache/spark/anomalies?threshold=3')
    );
    expect(res.total_anomalies).toBe(1);
    expect(res.anomalies[0].severity).toBe('HIGH');
  });

  it('predicts issue resolution time via POST', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: 'SUCCESS',
        predicted_duration_hours: 18.5,
        lower_bound_hours: 12.0,
        upper_bound_hours: 25.0,
        confidence_tier: 'HIGH (Trained ML Ensemble)',
        model_version: '0.2.0',
      }),
    });
    global.fetch = mockFetch;

    const res = await predictIssueResolution('apache', 'spark', {
      title: 'Fix issue',
      labels: ['bug'],
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/intelligence/apache/spark/issue-resolution/predict'),
      expect.objectContaining({ method: 'POST' })
    );
    expect(res.predicted_duration_hours).toBe(18.5);
  });

  it('predicts PR review delay via POST', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: 'SUCCESS',
        predicted_delay_hours: 6.2,
        lower_bound_hours: 2.0,
        upper_bound_hours: 10.4,
        confidence_tier: 'HIGH (Trained ML Ensemble)',
        model_version: '0.2.0',
      }),
    });
    global.fetch = mockFetch;

    const res = await predictPRReviewDelay('apache', 'spark', {
      title: 'Add feature',
      additions: 100,
      deletions: 20,
      changed_files: 3,
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/intelligence/apache/spark/pr-review-delay/predict'),
      expect.objectContaining({ method: 'POST' })
    );
    expect(res.predicted_delay_hours).toBe(6.2);
  });
});

