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
          bg: 'rgba(220, 38, 38, 0.15)',
          border: '#dc2626',
          color: '#ef4444',
        };
      case 'PullRequestEvent':
        return {
          label: 'New Git Pulled',
          icon: <GitPullRequest size={13} />,
          bg: '#18181b',
          border: '#27272a',
          color: '#ffffff',
        };
      case 'CommitCommentEvent':
      case 'CommitEvent':
        return {
          label: 'Committed',
          icon: <GitCommit size={13} />,
          bg: 'rgba(220, 38, 38, 0.12)',
          border: '#ef4444',
          color: '#ef4444',
        };
      case 'IssuesEvent':
        return {
          label: 'Issue',
          icon: <AlertCircle size={13} />,
          bg: '#18181b',
          border: '#27272a',
          color: '#ffffff',
        };
      case 'WatchEvent':
        return {
          label: 'Starred',
          icon: <Star size={13} />,
          bg: '#18181b',
          border: '#27272a',
          color: '#ffffff',
        };
      default:
        return {
          label: type.replace('Event', ''),
          icon: <GitCommit size={13} />,
          bg: '#18181b',
          border: '#27272a',
          color: '#a1a1aa',
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
        bg: 'rgba(220, 38, 38, 0.15)',
        color: '#ef4444',
        border: '1px solid #ef4444',
      };
    }
    if (evt.event_type === 'PullRequestEvent') {
      return {
        label: evt.action ? `PULLED: ${evt.action.toUpperCase()}` : 'PULLED',
        bg: '#18181b',
        color: '#ffffff',
        border: '1px solid #27272a',
      };
    }
    if (evt.action) {
      return {
        label: evt.action.toUpperCase(),
        bg: '#18181b',
        color: '#a1a1aa',
        border: '1px solid #27272a',
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
          color: '#a1a1aa',
          backgroundColor: '#121212',
          borderRadius: '12px',
          border: '1px solid #27272a',
        }}
      >
        Loading recent repository events...
      </div>
    );
  }

  return (
    <div
      style={{
        backgroundColor: '#121212',
        border: '1px solid #27272a',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
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
          borderBottom: '1px solid #27272a',
          backgroundColor: '#18181b',
        }}
      >
        {/* Type tabs */}
        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
          {[
            { id: 'All', label: 'All Events' },
            { id: 'PushEvent', label: 'New Git Pushed' },
            { id: 'PullRequestEvent', label: 'New Git Pulled' },
            { id: 'IssuesEvent', label: 'Issues' },
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
                    ? '1px solid #dc2626'
                    : '1px solid #27272a',
                backgroundColor:
                  selectedType === tab.id ? '#dc2626' : 'transparent',
                color: selectedType === tab.id ? '#ffffff' : '#a1a1aa',
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
            style={{ position: 'absolute', left: '0.65rem', top: '50%', transform: 'translateY(-50%)', color: '#a1a1aa' }}
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
              border: '1px solid #27272a',
              backgroundColor: '#121212',
              color: '#ffffff',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
      </div>

      {filteredEvents.length === 0 ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#a1a1aa', fontSize: '0.875rem' }}>
          No activity events found matching your filter criteria.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ backgroundColor: '#18181b', borderBottom: '1px solid #27272a' }}>
                <th style={{ padding: '0.75rem 1.25rem', fontSize: '0.72rem', color: '#a1a1aa', fontWeight: 600, letterSpacing: '0.05em' }}>
                  EVENT TYPE
                </th>
                <th style={{ padding: '0.75rem 1.25rem', fontSize: '0.72rem', color: '#a1a1aa', fontWeight: 600, letterSpacing: '0.05em' }}>
                  CONTRIBUTOR
                </th>
                <th style={{ padding: '0.75rem 1.25rem', fontSize: '0.72rem', color: '#a1a1aa', fontWeight: 600, letterSpacing: '0.05em' }}>
                  ACTIVITY SUMMARY
                </th>
                <th style={{ padding: '0.75rem 1.25rem', fontSize: '0.72rem', color: '#a1a1aa', fontWeight: 600, letterSpacing: '0.05em' }}>
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
                      borderBottom: '1px solid #27272a',
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
                              backgroundColor: 'rgba(220, 38, 38, 0.15)',
                              color: '#ef4444',
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
                        <span style={{ fontWeight: 600, color: '#ffffff' }}>{evt.actor}</span>
                      </div>
                    </td>

                    {/* Activity Summary */}
                    <td style={{ padding: '0.85rem 1.25rem', fontSize: '0.825rem', color: '#a1a1aa' }}>
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
                        <span style={{ color: '#ffffff', fontWeight: 500 }}>
                          {formatActivitySummary(evt)}
                        </span>
                      </div>
                    </td>

                    {/* Timestamp */}
                    <td style={{ padding: '0.85rem 1.25rem', fontSize: '0.75rem', color: '#a1a1aa', whiteSpace: 'nowrap' }}>
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
