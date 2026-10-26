import React, { useState, useMemo } from 'react';
import { Search, RefreshCw, Star, GitFork, ExternalLink, Check, Layers, Plus } from 'lucide-react';
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
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'active' | 'public'>('all');
  const [customRepoInput, setCustomRepoInput] = useState('');
  const [showAll, setShowAll] = useState(false);

  const formatPushDate = (isoStr: string | null): string => {
    if (!isoStr) return 'Never';
    try {
      const d = new Date(isoStr);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 30) return `${diffDays}d ago`;

      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoStr;
    }
  };

  const filteredRepositories = useMemo(() => {
    return repositories.filter((repo) => {
      const matchesSearch =
        repo.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (repo.description && repo.description.toLowerCase().includes(searchQuery.toLowerCase()));

      if (!matchesSearch) return false;

      if (filterType === 'active') return repo.is_active;
      if (filterType === 'public') return repo.visibility === 'public';
      return true;
    });
  }, [repositories, searchQuery, filterType]);

  const displayedRepositories = showAll
    ? filteredRepositories
    : filteredRepositories.slice(0, 8);

  const handleCustomRepoSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = customRepoInput.trim();
    if (trimmed && trimmed.includes('/')) {
      onSelectRepo(trimmed);
      setCustomRepoInput('');
    }
  };

  return (
    <section
      aria-label="Discovered Repositories Section"
      style={{
        backgroundColor: '#121212',
        border: '1px solid #27272a',
        borderRadius: '12px',
        padding: '1.5rem',
        marginBottom: '2rem',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.25rem',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: 'rgba(220, 38, 38, 0.12)',
              color: '#ef4444',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Layers size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0, color: '#ffffff' }}>
                Monitored Repositories
              </h2>
              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  padding: '0.15rem 0.55rem',
                  borderRadius: '9999px',
                  backgroundColor: '#18181b',
                  border: '1px solid #ef4444',
                  color: '#ef4444',
                }}
              >
                {repositories.length} Discovered
              </span>
            </div>
            <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.8rem', color: '#a1a1aa' }}>
              Select a repository to inspect developer velocity, code churn, and PR throughput.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          {/* Quick Track Input */}
          <form onSubmit={handleCustomRepoSubmit} style={{ display: 'flex', gap: '0.4rem' }}>
            <input
              type="text"
              placeholder="owner/repo to track..."
              value={customRepoInput}
              onChange={(e) => setCustomRepoInput(e.target.value)}
              aria-label="Track custom repository"
              style={{
                padding: '0.4rem 0.75rem',
                fontSize: '0.8rem',
                borderRadius: '6px',
                border: '1px solid #27272a',
                backgroundColor: '#18181b',
                color: '#ffffff',
                outline: 'none',
                width: '180px',
              }}
            />
            <button
              type="submit"
              disabled={!customRepoInput.includes('/')}
              aria-label="Track repository"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                padding: '0.4rem 0.65rem',
                fontSize: '0.8rem',
                fontWeight: 600,
                borderRadius: '6px',
                backgroundColor: customRepoInput.includes('/') ? '#dc2626' : '#27272a',
                color: '#ffffff',
                border: 'none',
                cursor: customRepoInput.includes('/') ? 'pointer' : 'not-allowed',
              }}
            >
              <Plus size={14} /> Track
            </button>
          </form>

          {/* Refresh button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing || isLoading}
            aria-label="Refresh discovered repositories"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
              padding: '0.45rem 0.9rem',
              fontSize: '0.825rem',
              fontWeight: 600,
              borderRadius: '6px',
              backgroundColor: isRefreshing ? '#27272a' : '#dc2626',
              color: '#ffffff',
              border: 'none',
              cursor: isRefreshing || isLoading ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
            }}
          >
            <RefreshCw size={13} style={{ animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }} />
            <span>{isRefreshing ? 'Syncing...' : '↻ Refresh Repositories'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            padding: '0.75rem 1rem',
            color: '#fca5a5',
            fontSize: '0.85rem',
            marginBottom: '1rem',
          }}
        >
          {error}
        </div>
      )}

      {/* Search & Filter Controls */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          marginBottom: '1rem',
          paddingBottom: '0.75rem',
          borderBottom: '1px solid #27272a',
        }}
      >
        <div style={{ position: 'relative', flex: '1', minWidth: '220px', maxWidth: '380px' }}>
          <Search
            size={15}
            style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#a1a1aa' }}
          />
          <input
            type="text"
            placeholder="Search discovered repositories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search repositories"
            style={{
              width: '100%',
              padding: '0.45rem 0.75rem 0.45rem 2.2rem',
              fontSize: '0.825rem',
              borderRadius: '8px',
              border: '1px solid #27272a',
              backgroundColor: '#18181b',
              color: '#ffffff',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          {(['all', 'active', 'public'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              style={{
                padding: '0.35rem 0.75rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                borderRadius: '6px',
                border: filterType === type ? '1px solid #dc2626' : '1px solid #27272a',
                backgroundColor: filterType === type ? '#dc2626' : 'transparent',
                color: filterType === type ? '#ffffff' : '#a1a1aa',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Grid of Repository Cards */}
      {isLoading ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: '#a1a1aa', fontSize: '0.9rem' }}>
          Loading repository inventory from Supabase/SQLite...
        </div>
      ) : displayedRepositories.length === 0 ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: '#a1a1aa', fontSize: '0.9rem' }}>
          No repositories matching &quot;{searchQuery}&quot;.
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '0.85rem',
          }}
        >
          {displayedRepositories.map((r) => {
            const isSelected = r.full_name === selectedRepo;

            return (
              <div
                key={r.id || r.full_name}
                onClick={() => onSelectRepo(r.full_name)}
                style={{
                  backgroundColor: isSelected
                    ? 'rgba(220, 38, 38, 0.08)'
                    : '#18181b',
                  border: isSelected
                    ? '1.5px solid #dc2626'
                    : '1px solid #27272a',
                  borderRadius: '10px',
                  padding: '1rem',
                  cursor: 'pointer',
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  boxShadow: 'none',
                  transition: 'all 0.15s ease',
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                    <h3
                      style={{
                        margin: 0,
                        fontSize: '0.925rem',
                        fontWeight: 700,
                        color: isSelected ? '#ef4444' : '#ffffff',
                        wordBreak: 'break-word',
                      }}
                    >
                      {r.full_name}
                    </h3>
                    {isSelected && (
                      <span
                        style={{
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          backgroundColor: '#dc2626',
                          color: '#ffffff',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        <Check size={12} strokeWidth={3} />
                      </span>
                    )}
                  </div>

                  {r.description && (
                    <p
                      style={{
                        margin: '0.4rem 0 0 0',
                        fontSize: '0.78rem',
                        color: '#a1a1aa',
                        overflow: 'hidden',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                      }}
                    >
                      {r.description}
                    </p>
                  )}
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: '0.75rem',
                    paddingTop: '0.5rem',
                    borderTop: '1px solid #27272a',
                    fontSize: '0.72rem',
                    color: '#a1a1aa',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                      <Star size={11} style={{ color: '#ef4444' }} /> {r.stars_count || 0}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                      <GitFork size={11} /> {r.forks_count || 0}
                    </span>
                    <span
                      style={{
                        padding: '0.1rem 0.4rem',
                        borderRadius: '4px',
                        backgroundColor: '#121212',
                        border: '1px solid #27272a',
                        color: '#ffffff',
                        fontSize: '0.65rem',
                        fontWeight: 600,
                      }}
                    >
                      {r.visibility}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span>Pushed: {formatPushDate(r.pushed_at)}</span>
                    {r.html_url && (
                      <a
                        href={r.html_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        style={{ color: '#a1a1aa', display: 'flex', alignItems: 'center' }}
                        title="View on GitHub"
                      >
                        <ExternalLink size={11} />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Show more toggle */}
      {filteredRepositories.length > 8 && (
        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
          <button
            onClick={() => setShowAll(!showAll)}
            style={{
              padding: '0.4rem 1rem',
              fontSize: '0.78rem',
              fontWeight: 600,
              borderRadius: '6px',
              backgroundColor: '#18181b',
              color: '#ef4444',
              border: '1px solid #dc2626',
              cursor: 'pointer',
            }}
          >
            {showAll ? 'Show Fewer' : `Show All ${filteredRepositories.length} Repositories`}
          </button>
        </div>
      )}
    </section>
  );
};
