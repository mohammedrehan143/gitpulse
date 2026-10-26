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
import { GitCommit, Users, Clock, Flame, Radio, Brain, Activity, RefreshCw } from 'lucide-react';
import {
  ForecastingCard,
  AnomalyCard,
  IssueIntelligenceCard,
  PRIntelligenceCard,
} from '../components/intelligence';
import {
  fetchActivityForecast,
  fetchAnomalies,
  fetchIssueResolutionInsights,
  predictIssueResolution,
  fetchPRReviewDelayInsights,
  predictPRReviewDelay,
  triggerModelTraining,
} from '../services/api';
import {
  ActivityForecastResponse,
  AnomalyResponse,
  IssueResolutionInsights,
  PRReviewDelayInsights,
} from '../types';

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

  // Tab View
  const [activeTab, setActiveTab] = useState<'overview' | 'intelligence'>('overview');

  // Intelligence State
  const [forecastData, setForecastData] = useState<ActivityForecastResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState<boolean>(false);
  const [forecastError, setForecastError] = useState<string | null>(null);
  const [forecastHorizon, setForecastHorizon] = useState<number>(7);

  const [anomalyData, setAnomalyData] = useState<AnomalyResponse | null>(null);
  const [anomalyLoading, setAnomalyLoading] = useState<boolean>(false);
  const [anomalyError, setAnomalyError] = useState<string | null>(null);
  const [anomalyThreshold, setAnomalyThreshold] = useState<number>(3.0);

  const [issueInsights, setIssueInsights] = useState<IssueResolutionInsights | null>(null);
  const [issueLoading, setIssueLoading] = useState<boolean>(false);

  const [prInsights, setPrInsights] = useState<PRReviewDelayInsights | null>(null);
  const [prLoading, setPrLoading] = useState<boolean>(false);

  const [isRetraining, setIsRetraining] = useState<boolean>(false);
  const [retrainMsg, setRetrainMsg] = useState<string | null>(null);

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

  // Load intelligence models data
  const loadIntelligenceData = useCallback(async () => {
    setForecastLoading(true);
    setAnomalyLoading(true);
    setIssueLoading(true);
    setPrLoading(true);

    fetchActivityForecast(owner, repo, forecastHorizon)
      .then((res) => setForecastData(res))
      .catch((err) => setForecastError(err.message))
      .finally(() => setForecastLoading(false));

    fetchAnomalies(owner, repo, anomalyThreshold)
      .then((res) => setAnomalyData(res))
      .catch((err) => setAnomalyError(err.message))
      .finally(() => setAnomalyLoading(false));

    fetchIssueResolutionInsights(owner, repo)
      .then((res) => setIssueInsights(res))
      .catch(() => {})
      .finally(() => setIssueLoading(false));

    fetchPRReviewDelayInsights(owner, repo)
      .then((res) => setPrInsights(res))
      .catch(() => {})
      .finally(() => setPrLoading(false));
  }, [owner, repo, forecastHorizon, anomalyThreshold]);

  useEffect(() => {
    if (activeTab === 'intelligence') {
      loadIntelligenceData();
    }
  }, [activeTab, loadIntelligenceData]);

  const handleRetrainAll = async () => {
    setIsRetraining(true);
    setRetrainMsg(null);
    try {
      await triggerModelTraining(owner, repo);
      setRetrainMsg('All analytical models retrained and persisted successfully!');
      loadIntelligenceData();
    } catch (err: unknown) {
      setRetrainMsg(err instanceof Error ? err.message : 'Retraining failed');
    } finally {
      setIsRetraining(false);
    }
  };

  // Reset AI insights when repository changes
  useEffect(() => {
    setAiInsights(null);
    setAiError(null);
    setRetrainMsg(null);
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

      {/* Platform Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '1.5rem',
          borderBottom: '1px solid #27272a',
          paddingBottom: '8px',
        }}
      >
        <button
          onClick={() => setActiveTab('overview')}
          style={{
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: 700,
            borderRadius: '6px',
            border: activeTab === 'overview' ? '1px solid #dc2626' : '1px solid #27272a',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            backgroundColor: activeTab === 'overview' ? '#dc2626' : '#141414',
            color: '#ffffff',
            transition: 'all 0.15s ease',
          }}
        >
          <Activity size={16} />
          Velocity & Live Streams
        </button>

        <button
          onClick={() => setActiveTab('intelligence')}
          style={{
            padding: '8px 16px',
            fontSize: '13px',
            fontWeight: 700,
            borderRadius: '6px',
            border: activeTab === 'intelligence' ? '1px solid #dc2626' : '1px solid #27272a',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            backgroundColor: activeTab === 'intelligence' ? '#dc2626' : '#141414',
            color: '#ffffff',
            transition: 'all 0.15s ease',
          }}
        >
          <Brain size={16} />
          Data Science Intelligence Suite
          <span
            style={{
              padding: '2px 6px',
              fontSize: '10px',
              backgroundColor: activeTab === 'intelligence' ? '#ffffff' : '#27272a',
              color: activeTab === 'intelligence' ? '#000000' : '#ffffff',
              borderRadius: '4px',
              fontWeight: 800,
            }}
          >
            4 ML MODULES
          </span>
        </button>
      </div>

      {activeTab === 'intelligence' ? (
        <section style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginBottom: '2rem' }}>
          {/* Top Control Bar for Retraining */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '14px 18px',
              backgroundColor: '#121212',
              borderRadius: '8px',
              border: '1px solid #27272a',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div>
              <div style={{ fontWeight: 700, color: '#ffffff', fontSize: '14px' }}>
                Engineering Machine Learning Models for {selectedRepo}
              </div>
              <div style={{ fontSize: '12px', color: '#a1a1aa' }}>
                Forecasting, Anomaly Detection, Issue Turnaround & PR Review Models
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {retrainMsg && (
                <span style={{ fontSize: '12px', color: '#ffffff', fontWeight: 600 }}>
                  {retrainMsg}
                </span>
              )}
              <button
                onClick={handleRetrainAll}
                disabled={isRetraining}
                style={{
                  padding: '7px 16px',
                  backgroundColor: '#dc2626',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: 700,
                  fontSize: '12px',
                  cursor: isRetraining ? 'not-allowed' : 'pointer',
                  opacity: isRetraining ? 0.7 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <RefreshCw size={14} />
                {isRetraining ? 'Retraining ML Models...' : 'Retrain All Models'}
              </button>
            </div>
          </div>

          {/* Module A: Forecasting */}
          <ForecastingCard
            data={forecastData}
            loading={forecastLoading}
            error={forecastError}
            horizon={forecastHorizon}
            onHorizonChange={(h) => setForecastHorizon(h)}
          />

          {/* Module B: Anomalies */}
          <AnomalyCard
            data={anomalyData}
            loading={anomalyLoading}
            error={anomalyError}
            threshold={anomalyThreshold}
            onThresholdChange={(t) => setAnomalyThreshold(t)}
          />

          {/* Bottom Grid for Module C & Module D */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
              gap: '24px',
            }}
          >
            {/* Module C: Issue Resolution Duration */}
            <IssueIntelligenceCard
              insights={issueInsights}
              loading={issueLoading}
              onPredict={(title, labels) => predictIssueResolution(owner, repo, { title, labels })}
            />

            {/* Module D: PR First-Review Delay */}
            <PRIntelligenceCard
              insights={prInsights}
              loading={prLoading}
              onPredict={(title, adds, dels, files) =>
                predictPRReviewDelay(owner, repo, {
                  title,
                  additions: adds,
                  deletions: dels,
                  changed_files: files,
                })
              }
            />
          </div>
        </section>
      ) : (
        <>
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
            <div style={{ display: 'flex', gap: '0.3rem', backgroundColor: '#121212', padding: '0.25rem', borderRadius: '6px', border: '1px solid #27272a' }}>
              {(['7d', '14d', '30d', '90d'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTimeframe(t)}
                  style={{
                    padding: '0.3rem 0.65rem',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: timeframe === t ? '#dc2626' : 'transparent',
                    color: timeframe === t ? '#ffffff' : '#a1a1aa',
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

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: wsConnected ? '#ffffff' : '#a1a1aa' }}>
                <Radio size={12} color="#ef4444" />
                <span>{wsConnected ? 'Live Feed Connected' : 'Feed Updated'}</span>
              </div>
            </div>
            <RecentEventsTable events={events} loading={eventsLoading} />
          </section>
        </>
      )}
    </MainLayout>
  );
};
