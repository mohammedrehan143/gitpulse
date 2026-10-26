import React, { useState, useEffect, useCallback } from 'react';
import { MainLayout } from '../layouts/MainLayout';
import { MetricsCard } from '../components/MetricsCard';
import { CommitVelocityChart } from '../charts/CommitVelocityChart';
import { ActivityChart } from '../charts/ActivityChart';
import { RecentEventsTable } from '../components/RecentEventsTable';
import { RepositoryList } from '../components/RepositoryList';
import { AIInsightsCard } from '../components/AIInsightsCard';
import { useRepoMetrics } from '../hooks/useRepoMetrics';
import {
  fetchRepositoryEvents,
  fetchDiscoveredRepositories,
  refreshDiscoveredRepositories,
  fetchAIInsights,
  createRepoWebSocket,
} from '../services/api';
import { EventItem, DiscoveredRepository, AIInsightsResponse } from '../types';
import { GitCommit, Users, Clock, Flame, Radio } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [repositories, setRepositories] = useState<DiscoveredRepository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>('apache/spark');
  const [reposLoading, setReposLoading] = useState<boolean>(true);
  const [repoError, setRepoError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Timeframe selector
  const [timeframe, setTimeframe] = useState<'7d' | '14d' | '30d' | '90d'>('30d');

  // Events & WebSocket
  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventsLoading, setEventsLoading] = useState<boolean>(true);
  const [wsConnected, setWsConnected] = useState<boolean>(false);

  // AI Insights State
  const [aiInsights, setAiInsights] = useState<AIInsightsResponse | null>(null);
  const [aiLoading, setAiLoading] = useState<boolean>(false);
  const [aiError, setAiError] = useState<string | null>(null);

  // Load discovered repositories on mount
  useEffect(() => {
    fetchDiscoveredRepositories()
      .then((res) => {
        setRepositories(res.repositories);
        if (res.repositories.length > 0) {
          // Default to first active repository if available
          const firstActive = res.repositories.find((r) => r.is_active) || res.repositories[0];
          setSelectedRepo(firstActive.full_name);
        }
        setReposLoading(false);
      })
      .catch((err) => {
        setRepoError(err.message || 'Failed to load discovered repositories');
        setReposLoading(false);
      });
  }, []);

  const handleRefreshRepositories = async () => {
    setIsRefreshing(true);
    setRepoError(null);
    try {
      const res = await refreshDiscoveredRepositories();
      setRepositories(res.repositories);
      if (res.repositories.length > 0 && !res.repositories.some((r) => r.full_name === selectedRepo)) {
        setSelectedRepo(res.repositories[0].full_name);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to refresh repositories';
      setRepoError(msg);
    } finally {
      setIsRefreshing(false);
    }
  };

  const [owner, repo] = selectedRepo.includes('/') ? selectedRepo.split('/') : ['apache', 'spark'];
  const { data: metrics, loading: metricsLoading, error: metricsError } = useRepoMetrics(owner, repo, timeframe);

  // Load recent events
  useEffect(() => {
    setEventsLoading(true);
    fetchRepositoryEvents(owner, repo, 20)
      .then((res) => {
        setEvents(res.events);
        setEventsLoading(false);
      })
      .catch(() => {
        setEventsLoading(false);
      });
  }, [owner, repo]);

  // Connect live WebSocket stream for selected repository
  useEffect(() => {
    setWsConnected(false);
    const ws = createRepoWebSocket(
      owner,
      repo,
      (data: unknown) => {
        setWsConnected(true);
        const msg = data as { type?: string; event?: EventItem };
        if (msg && msg.type === 'event_stream' && msg.event) {
          setEvents((prev) => [msg.event as EventItem, ...prev.slice(0, 29)]);
        }
      },
      () => {
        setWsConnected(false);
      }
    );

    if (ws) {
      setWsConnected(true);
    }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [owner, repo]);

  // Trigger Groq AI velocity insights
  const handleGenerateAIInsights = useCallback(async () => {
    setAiLoading(true);
    setAiError(null);
    try {
      const res = await fetchAIInsights(owner, repo);
      setAiInsights(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate AI insights';
      setAiError(msg);
    } finally {
      setAiLoading(false);
    }
  }, [owner, repo]);

  // Reset AI insights when repository changes
  useEffect(() => {
    setAiInsights(null);
    setAiError(null);
  }, [owner, repo]);

  return (
    <MainLayout
      currentRepo={selectedRepo}
      wsConnected={wsConnected}
      onRefreshAll={handleRefreshRepositories}
      isRefreshing={isRefreshing}
    >
      {metricsError && (
        <div
          role="alert"
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            padding: '1rem',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            fontSize: '0.875rem',
          }}
        >
          {metricsError}
        </div>
      )}

      {/* Discovered & Monitored Repositories Management */}
      <RepositoryList
        repositories={repositories}
        selectedRepo={selectedRepo}
        onSelectRepo={(newRepo) => setSelectedRepo(newRepo)}
        onRefresh={handleRefreshRepositories}
        isRefreshing={isRefreshing}
        isLoading={reposLoading}
        error={repoError}
      />

      {/* Top Velocity Metrics Cards & Timeframe Selector Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
            Velocity Overview
          </h2>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            ({timeframe} rolling window)
          </span>
        </div>

        {/* Timeframe pills */}
        <div style={{ display: 'flex', gap: '0.3rem', backgroundColor: 'rgba(15, 23, 42, 0.6)', padding: '0.2rem', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.15)' }}>
          {(['7d', '14d', '30d', '90d'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTimeframe(t)}
              style={{
                padding: '0.3rem 0.65rem',
                fontSize: '0.75rem',
                fontWeight: 700,
                borderRadius: '6px',
                border: 'none',
                backgroundColor: timeframe === t ? '#0284c7' : 'transparent',
                color: timeframe === t ? '#ffffff' : '#94a3b8',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {t.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1rem',
          marginBottom: '2rem',
        }}
      >
        <MetricsCard
          label={`Total Commits (${timeframe})`}
          value={metrics ? metrics.summary.total_commits : '...'}
          subtext="+14% vs previous period"
          trend="up"
          icon={<GitCommit size={16} />}
        />
        <MetricsCard
          label="Active Contributors"
          value={metrics ? metrics.summary.active_contributors : '...'}
          subtext="Healthy collaboration ratio"
          trend="neutral"
          icon={<Users size={16} />}
        />
        <MetricsCard
          label="Avg PR Cycle Time"
          value={metrics ? `${metrics.summary.avg_pr_cycle_time_hours}h` : '...'}
          subtext="-2.4h turnaround speed"
          trend="up"
          icon={<Clock size={16} />}
        />
        <MetricsCard
          label="Code Churn Rate"
          value={metrics ? `${(metrics.summary.churn_rate * 100).toFixed(0)}%` : '...'}
          subtext="Refactoring efficiency"
          trend="neutral"
          icon={<Flame size={16} />}
        />
      </section>

      {/* Groq AI Velocity Copilot Panel */}
      <AIInsightsCard
        insights={aiInsights}
        loading={aiLoading}
        error={aiError}
        onGenerate={handleGenerateAIInsights}
        repoFullName={selectedRepo}
      />

      {/* Visualizations Grid */}
      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem',
        }}
      >
        <CommitVelocityChart
          timeline={metrics ? metrics.timeline : []}
          loading={metricsLoading}
        />
        <ActivityChart
          timeline={metrics ? metrics.timeline : []}
        />
      </section>

      {/* Live Activity Stream Table */}
      <section>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
          }}
        >
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
              Live Activity Stream
            </h2>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              Real-time event stream persisted in Supabase / SQLite
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: wsConnected ? '#34d399' : '#94a3b8' }}>
            <Radio size={12} />
            <span>{wsConnected ? 'Streaming Live' : 'Feed Updated'}</span>
          </div>
        </div>
        <RecentEventsTable events={events} loading={eventsLoading} />
      </section>
    </MainLayout>
  );
};
