import React from 'react';
import { DiscoveredRepository } from '../types';

interface RepositoryListProps {
  repositories: DiscoveredRepository[];
  selectedRepo: string;
  onSelectRepo: (fullName: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  isLoading: boolean;
  error: string | null;
}

export const RepositoryList: React.FC<RepositoryListProps> = ({
  repositories,
  selectedRepo,
  onSelectRepo,
  onRefresh,
  isRefreshing,
  isLoading,
  error,
}) => {
  const formatPushDate = (isoStr: string | null): string => {
    if (!isoStr) return 'Never';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <section
      aria-label="Discovered Repositories Section"
      style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '8px',
        padding: '1.25rem',
        marginBottom: '2rem',
      }}
    >
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0, color: '#f8fafc' }}>
            Discovered Repositories
          </h2>
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              padding: '0.2rem 0.6rem',
              borderRadius: '9999px',
              backgroundColor: '#0369a1',
              color: '#e0f2fe',
            }}
          >
            {repositories.length} Discovered
          </span>
        </div>

        <button
          onClick={onRefresh}
          disabled={isRefreshing || isLoading}
          aria-label="Refresh discovered repositories"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.45rem 0.9rem',
            fontSize: '0.875rem',
            fontWeight: 500,
            borderRadius: '6px',
            backgroundColor: isRefreshing ? '#475569' : '#2563eb',
            color: '#ffffff',
            border: 'none',
            cursor: isRefreshing || isLoading ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s',
          }}
        >
          {isRefreshing ? (
            <>
              <span
                style={{
                  display: 'inline-block',
                  width: '12px',
                  height: '12px',
                  border: '2px solid #ffffff',
                  borderTopColor: 'transparent',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                }}
              />
              Syncing...
            </>
          ) : (
            '↻ Refresh Repositories'
          )}
        </button>
      </div>

      {error && (
        <div
          role="alert"
          style={{
            backgroundColor: '#7f1d1d',
            color: '#fecaca',
            padding: '0.75rem 1rem',
            borderRadius: '6px',
            marginBottom: '1rem',
            fontSize: '0.875rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{error}</span>
          <button
            onClick={onRefresh}
            style={{
              background: 'transparent',
              border: '1px solid #fecaca',
              color: '#fecaca',
              borderRadius: '4px',
              padding: '0.2rem 0.5rem',
              cursor: 'pointer',
              fontSize: '0.75rem',
            }}
          >
            Retry
          </button>
        </div>
      )}

      {isLoading && (
        <div
          style={{
            padding: '2rem',
            textAlign: 'center',
            color: '#94a3b8',
            fontSize: '0.875rem',
          }}
        >
          Discovering repositories from authenticated account...
        </div>
      )}

      {!isLoading && repositories.length === 0 && !error && (
        <div
          style={{
            padding: '2rem',
            textAlign: 'center',
            color: '#94a3b8',
            border: '1px dashed #475569',
            borderRadius: '6px',
          }}
        >
          <p style={{ margin: '0 0 0.5rem 0', fontWeight: 500 }}>No repositories discovered yet.</p>
          <span style={{ fontSize: '0.875rem' }}>
            Check your GITHUB_TOKEN permissions or trigger a manual refresh above.
          </span>
        </div>
      )}

      {!isLoading && repositories.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '1rem',
          }}
        >
          {repositories.map((repo) => {
            const isSelected = selectedRepo === repo.full_name;
            const isPrivate = repo.visibility.toLowerCase() === 'private';
            const isPolling = repo.monitoring_status === 'POLLING' || repo.monitoring_status === 'WEBHOOK_ACTIVE';

            return (
              <div
                key={repo.id || repo.full_name}
                onClick={() => onSelectRepo(repo.full_name)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    onSelectRepo(repo.full_name);
                  }
                }}
                style={{
                  border: isSelected ? '2px solid #38bdf8' : '1px solid #334155',
                  borderRadius: '6px',
                  padding: '1rem',
                  backgroundColor: isSelected ? '#1e293b' : '#0f172a',
                  cursor: 'pointer',
                  transition: 'border-color 0.15s, transform 0.15s',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      marginBottom: '0.5rem',
                      gap: '0.5rem',
                    }}
                  >
                    <strong
                      style={{
                        color: isSelected ? '#38bdf8' : '#f1f5f9',
                        fontSize: '0.95rem',
                        wordBreak: 'break-all',
                      }}
                    >
                      {repo.full_name}
                    </strong>
                    <div style={{ display: 'flex', gap: '0.35rem', flexShrink: 0 }}>
                      <span
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          padding: '0.15rem 0.45rem',
                          borderRadius: '4px',
                          backgroundColor: isPrivate ? '#451a03' : '#064e3b',
                          color: isPrivate ? '#fde68a' : '#a7f3d0',
                          border: `1px solid ${isPrivate ? '#78350f' : '#047857'}`,
                        }}
                      >
                        {repo.visibility}
                      </span>
                    </div>
                  </div>

                  <p
                    style={{
                      fontSize: '0.8rem',
                      color: '#94a3b8',
                      margin: '0 0 0.75rem 0',
                      lineHeight: 1.4,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {repo.description || 'No description provided'}
                  </p>
                </div>

                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderTop: '1px solid #1e293b',
                    paddingTop: '0.5rem',
                    fontSize: '0.75rem',
                    color: '#64748b',
                  }}
                >
                  <div>
                    <span>Pushed: </span>
                    <span style={{ color: '#cbd5e1' }}>{formatPushDate(repo.pushed_at)}</span>
                  </div>

                  <span
                    style={{
                      padding: '0.15rem 0.4rem',
                      borderRadius: '4px',
                      backgroundColor: isPolling ? '#0f766e' : '#334155',
                      color: isPolling ? '#ccfbf1' : '#94a3b8',
                      fontWeight: 500,
                      fontSize: '0.7rem',
                    }}
                  >
                    {repo.monitoring_status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
