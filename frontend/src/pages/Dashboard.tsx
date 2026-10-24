import React, { useState, useEffect } from 'react';
import { MainLayout } from '../layouts/MainLayout';
import { MetricsCard } from '../components/MetricsCard';
import { CommitVelocityChart } from '../charts/CommitVelocityChart';
import { ActivityChart } from '../charts/ActivityChart';
import { RecentEventsTable } from '../components/RecentEventsTable';
import { useRepoMetrics } from '../hooks/useRepoMetrics';
import { fetchRepositoryEvents } from '../services/api';
import { EventItem } from '../types';

export const Dashboard: React.FC = () => {
  const [selectedRepo] = useState<string>('apache/spark');
  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventsLoading, setEventsLoading] = useState<boolean>(true);

  const [owner, repo] = selectedRepo.split('/');
  const { data: metrics, loading: metricsLoading, error } = useRepoMetrics(owner, repo);

  useEffect(() => {
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
      {error && (
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
          {error}
        </div>
      )}

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
