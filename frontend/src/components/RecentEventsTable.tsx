import React, { useState, useMemo } from 'react';
import { GitCommit, GitPullRequest, AlertCircle, Star, Search, Clock, User } from 'lucide-react';
import { EventItem } from '../types';

interface RecentEventsTableProps {
  events: EventItem[];
  loading?: boolean;
}

export const RecentEventsTable: React.FC<RecentEventsTableProps> = ({ events, loading }) => {
  const [selectedType, setSelectedType] = useState<string>('All');
  const [searchActor, setSearchActor] = useState<string>('');

  const formatRelativeTime = (isoStr: string): string => {
    try {
      const date = new Date(isoStr);
      const now = new Date();
      const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

      if (diffSeconds < 60) return 'Just now';
      if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
      if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
      if (diffSeconds < 604800) return `${Math.floor(diffSeconds / 86400)}d ago`;

      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return isoStr;
    }
  };

  const getEventBadge = (type: string) => {
    switch (type) {
      case 'PushEvent':
        return {
          label: 'New Git Pushed',
          icon: <GitCommit size={13} />,
          bg: 'rgba(56, 189, 248, 0.12)',
          border: 'rgba(56, 189, 248, 0.35)',
          color: '#38bdf8',
        };
      case 'PullRequestEvent':
        return {
          label: 'New Git Pulled',
          icon: <GitPullRequest size={13} />,
          bg: 'rgba(168, 85, 247, 0.12)',
          border: 'rgba(168, 85, 247, 0.35)',
          color: '#c084fc',
        };
      case 'CommitCommentEvent':
      case 'CommitEvent':
        return {
          label: 'Committed',
          icon: <GitCommit size={13} />,
          bg: 'rgba(16, 185, 129, 0.12)',
          border: 'rgba(16, 185, 129, 0.35)',
          color: '#34d399',
        };
      case 'IssuesEvent':
        return {
          label: 'Issue',
          icon: <AlertCircle size={13} />,
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.35)',
          color: '#fbbf24',
        };
      case 'WatchEvent':
        return {
          label: 'Starred',
          icon: <Star size={13} />,
          bg: 'rgba(234, 179, 8, 0.12)',
          border: 'rgba(234, 179, 8, 0.35)',
          color: '#fde047',
        };
      default:
        return {
          label: type.replace('Event', ''),
          icon: <GitCommit size={13} />,
          bg: 'rgba(148, 163, 184, 0.12)',
          border: 'rgba(148, 163, 184, 0.35)',
          color: '#94a3b8',
        };
    }
  };

  const formatActivitySummary = (evt: EventItem) => {
    const summary = evt.payload_summary || '';
    if (
      summary.startsWith('New git pushed') ||
      summary.startsWith('New git pulled') ||
      summary.startsWith('New git committed')
    ) {
      return summary;
    }

    if (evt.event_type === 'PushEvent') {
      return `New git pushed: commits committed by ${evt.actor}`;
    }
    if (evt.event_type === 'PullRequestEvent') {
      return `New git pulled: PR ${evt.action || 'activity'} by ${evt.actor}`;
    }
    if (evt.event_type === 'CommitCommentEvent' || evt.event_type === 'CommitEvent') {
      return `New git committed: ${evt.actor} committed changes`;
    }
    return summary || `${evt.event_type} by ${evt.actor}`;
  };

  const getActionChip = (evt: EventItem) => {
    if (evt.event_type === 'PushEvent') {
      return {
        label: 'COMMITTED',
        bg: 'rgba(56, 189, 248, 0.15)',
        color: '#38bdf8',
        border: '1px solid rgba(56, 189, 248, 0.25)',
      };
    }
    if (evt.event_type === 'PullRequestEvent') {
      return {
        label: evt.action ? `PULLED: ${evt.action.toUpperCase()}` : 'PULLED',
        bg: 'rgba(168, 85, 247, 0.15)',
        color: '#c084fc',
        border: '1px solid rgba(168, 85, 247, 0.25)',
      };
    }
    if (evt.action) {
      return {
        label: evt.action.toUpperCase(),
        bg: 'rgba(30, 41, 59, 0.8)',
        color: '#94a3b8',
        border: '1px solid rgba(148, 163, 184, 0.15)',
      };
    }
    return null;
  };

  const filteredEvents = useMemo(() => {
    return (events || []).filter((e) => {
      const matchesType = selectedType === 'All' || e.event_type === selectedType;
      const matchesSearch =
        !searchActor ||
        e.actor.toLowerCase().includes(searchActor.toLowerCase()) ||
        (e.payload_summary && e.payload_summary.toLowerCase().includes(searchActor.toLowerCase()));
      return matchesType && matchesSearch;
    });
  }, [events, selectedType, searchActor]);

  if (loading) {
    return (
      <div
        style={{
          padding: '3rem',
          textAlign: 'center',
          color: '#94a3b8',
          backgroundColor: 'rgba(15, 23, 42, 0.75)',
          borderRadius: '12px',
          border: '1px solid rgba(148, 163, 184, 0.15)',
        }}
      >
        Loading recent repository events...
      </div>
    );
  }

  return (
    <div
      style={{
        backgroundColor: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(8px)',
        border: '1px solid rgba(148, 163, 184, 0.15)',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
      }}
    >
      {/* Search & Event Type Tabs */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          padding: '1rem 1.25rem',
          borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
          backgroundColor: 'rgba(15, 23, 42, 0.5)',
        }}
      >
        {/* Type tabs */}
        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
          {[
            { id: 'All', label: 'All Events' },
            { id: 'PushEvent', label: '🚀 New Git Pushed' },
            { id: 'PullRequestEvent', label: '📥 New Git Pulled' },
            { id: 'IssuesEvent', label: '⚠️ Issues' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedType(tab.id)}
              style={{
                padding: '0.35rem 0.75rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                borderRadius: '6px',
                border:
                  selectedType === tab.id
                    ? '1px solid #38bdf8'
                    : '1px solid rgba(148, 163, 184, 0.2)',
                backgroundColor:
                  selectedType === tab.id ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: selectedType === tab.id ? '#38bdf8' : '#94a3b8',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div style={{ position: 'relative', width: '220px' }}>
          <Search
            size={14}
            style={{ position: 'absolute', left: '0.65rem', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }}
          />
          <input
            type="text"
            placeholder="Search events or actors..."
            value={searchActor}
            onChange={(e) => setSearchActor(e.target.value)}
            style={{
              width: '100%',
              padding: '0.35rem 0.65rem 0.35rem 2rem',
              fontSize: '0.78rem',
              borderRadius: '6px',
              border: '1px solid rgba(148, 163, 184, 0.2)',
              backgroundColor: 'rgba(30, 41, 59, 0.6)',
              color: '#f8fafc',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
      </div>

      {filteredEvents.length === 0 ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.875rem' }}>
          No activity events found matching your filter criteria.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}>
                <th style={{ padding: '0.75rem 1.25rem', fontSize: '0.72rem', color: '#64748b', fontWeight: 600, letterSpacing: '0.05em' }}>
                  EVENT TYPE
                </th>
                <th style={{ padding: '0.75rem 1.25rem', fontSize: '0.72rem', color: '#64748b', fontWeight: 600, letterSpacing: '0.05em' }}>
                  CONTRIBUTOR
                </th>
                <th style={{ padding: '0.75rem 1.25rem', fontSize: '0.72rem', color: '#64748b', fontWeight: 600, letterSpacing: '0.05em' }}>
                  ACTIVITY SUMMARY
                </th>
                <th style={{ padding: '0.75rem 1.25rem', fontSize: '0.72rem', color: '#64748b', fontWeight: 600, letterSpacing: '0.05em' }}>
                  TIMESTAMP
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.map((evt) => {
                const badge = getEventBadge(evt.event_type);

                return (
                  <tr
                    key={evt.event_id}
                    style={{
                      borderBottom: '1px solid rgba(148, 163, 184, 0.08)',
                      transition: 'background-color 0.15s ease',
                    }}
                  >
                    {/* Event Type Badge */}
                    <td style={{ padding: '0.85rem 1.25rem', fontSize: '0.825rem' }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.4rem',
                          padding: '0.25rem 0.65rem',
                          borderRadius: '9999px',
                          backgroundColor: badge.bg,
                          border: `1px solid ${badge.border}`,
                          color: badge.color,
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {badge.icon}
                        <span>{badge.label}</span>
                      </span>
                    </td>

                    {/* Actor */}
                    <td style={{ padding: '0.85rem 1.25rem', fontSize: '0.825rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {evt.actor_avatar_url ? (
                          <img
                            src={evt.actor_avatar_url}
                            alt={evt.actor}
                            style={{ width: '22px', height: '22px', borderRadius: '50%' }}
                          />
                        ) : (
                          <div
                            style={{
                              width: '22px',
                              height: '22px',
                              borderRadius: '50%',
                              backgroundColor: 'rgba(56, 189, 248, 0.2)',
                              color: '#38bdf8',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '0.65rem',
                              fontWeight: 700,
                            }}
                          >
                            <User size={12} />
                          </div>
                        )}
                        <span style={{ fontWeight: 600, color: '#f8fafc' }}>{evt.actor}</span>
                      </div>
                    </td>

                    {/* Activity Summary */}
                    <td style={{ padding: '0.85rem 1.25rem', fontSize: '0.825rem', color: '#cbd5e1' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                        {(() => {
                          const chip = getActionChip(evt);
                          if (!chip) return null;
                          return (
                            <span
                              style={{
                                fontSize: '0.68rem',
                                padding: '0.15rem 0.45rem',
                                borderRadius: '4px',
                                backgroundColor: chip.bg,
                                color: chip.color,
                                border: chip.border,
                                textTransform: 'uppercase',
                                fontWeight: 700,
                                letterSpacing: '0.04em',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {chip.label}
                            </span>
                          );
                        })()}
                        <span style={{ color: '#f1f5f9', fontWeight: 500 }}>
                          {formatActivitySummary(evt)}
                        </span>
                      </div>
                    </td>

                    {/* Timestamp */}
                    <td style={{ padding: '0.85rem 1.25rem', fontSize: '0.75rem', color: '#64748b', whiteSpace: 'nowrap' }}>
                      <span
                        style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                        title={new Date(evt.created_at).toLocaleString()}
                      >
                        <Clock size={12} />
                        {formatRelativeTime(evt.created_at)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
