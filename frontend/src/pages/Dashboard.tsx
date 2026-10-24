import React, { useState, useEffect } from 'react';
import { MainLayout } from '../layouts/MainLayout';
import { MetricsCard } from '../components/MetricsCard';
import { CommitVelocityChart } from '../charts/CommitVelocityChart';
import { ActivityChart } from '../charts/ActivityChart';
import { RecentEventsTable } from '../components/RecentEventsTable';
import { RepositoryList } from '../components/RepositoryList';
import { useRepoMetrics } from '../hooks/useRepoMetrics';
import { fetchRepositoryEvents, fetchDiscoveredRepositories, refreshDiscoveredRepositories } from '../services/api';
import { EventItem, DiscoveredRepository } from '../types';

export const Dashboard: React.FC = () => {
  const [repositories, setRepositories] = useState<DiscoveredRepository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>('apache/spark');
  const [reposLoading, setReposLoading] = useState<boolean>(true);
  const [repoError, setRepoError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventsLoading, setEventsLoading] = useState<boolean>(true);

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
  const { data: metrics, loading: metricsLoading, error: metricsError } = useRepoMetrics(owner, repo);

  useEffect(() => {
    setEventsLoading(true);
    fetchRepositoryEvents(owner, repo, 10)
      .then((res) => {
        setEvents(res.events);
        setEventsLoading(false);
      })
      .catch(() => {
        setEventsLoading(false);
      });
  }, [owner, repo]);

  return (
    <MainLayout currentRepo={selectedRepo}>
      {metricsError && (
        <div
          role="alert"
          style={{
            backgroundColor: '#7f1d1d',
            color: '#fecaca',
            padding: '1rem',
            borderRadius: '6px',
            marginBottom: '1.5rem',
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

      {/* Top Velocity Metrics Cards */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <MetricsCard
          label="Total Commits (30d)"
          value={metrics ? metrics.summary.total_commits : '...'}
          subtext="+14% vs previous 30d"
          trend="up"
        />
        <MetricsCard
          label="Active Contributors"
          value={metrics ? metrics.summary.active_contributors : '...'}
          subtext="Across 18 pull requests"
          trend="neutral"
        />
        <MetricsCard
          label="Avg PR Cycle Time"
          value={metrics ? `${metrics.summary.avg_pr_cycle_time_hours}h` : '...'}
          subtext="-2.4h turnaround speed"
          trend="up"
        />
        <MetricsCard
          label="Code Churn Rate"
          value={metrics ? `${(metrics.summary.churn_rate * 100).toFixed(0)}%` : '...'}
          subtext="Healthy refactoring ratio"
          trend="neutral"
        />
      </section>

      {/* Visualizations Grid */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>Recent Activity Stream</h2>
          <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Real-time event feed</span>
        </div>
        <RecentEventsTable events={events} loading={eventsLoading} />
      </section>
    </MainLayout>
  );
};
