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
          icon: <GitCommit size={13} />,
          bg: 'rgba(56, 189, 248, 0.12)',
          border: 'rgba(56, 189, 248, 0.3)',
          color: '#38bdf8',
        };
      case 'PullRequestEvent':
        return {
          icon: <GitPullRequest size={13} />,
          bg: 'rgba(168, 85, 247, 0.12)',
          border: 'rgba(168, 85, 247, 0.3)',
          color: '#c084fc',
        };
      case 'IssuesEvent':
        return {
          icon: <AlertCircle size={13} />,
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.3)',
          color: '#fbbf24',
        };
      case 'WatchEvent':
        return {
          icon: <Star size={13} />,
          bg: 'rgba(234, 179, 8, 0.12)',
          border: 'rgba(234, 179, 8, 0.3)',
          color: '#fde047',
        };
      default:
        return {
          icon: <GitCommit size={13} />,
          bg: 'rgba(148, 163, 184, 0.12)',
          border: 'rgba(148, 163, 184, 0.3)',
          color: '#94a3b8',
        };
    }
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
          {['All', 'PushEvent', 'PullRequestEvent', 'IssuesEvent'].map((type) => (
            <button
              key={type}
              onClick={() => setSelectedType(type)}
              style={{
                padding: '0.35rem 0.75rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                borderRadius: '6px',
                border: selectedType === type ? '1px solid #38bdf8' : '1px solid rgba(148, 163, 184, 0.2)',
                backgroundColor: selectedType === type ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: selectedType === type ? '#38bdf8' : '#94a3b8',
                cursor: 'pointer',
              }}
            >
              {type === 'All' ? 'All Events' : type.replace('Event', '')}
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
                          gap: '0.35rem',
                          padding: '0.2rem 0.6rem',
                          borderRadius: '9999px',
                          backgroundColor: badge.bg,
                          border: `1px solid ${badge.border}`,
                          color: badge.color,
                          fontSize: '0.75rem',
                          fontWeight: 600,
                        }}
                      >
                        {badge.icon}
                        <span>{evt.event_type.replace('Event', '')}</span>
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

                    {/* Payload Summary */}
                    <td style={{ padding: '0.85rem 1.25rem', fontSize: '0.825rem', color: '#cbd5e1' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {evt.action && (
                          <span
                            style={{
                              fontSize: '0.68rem',
                              padding: '0.1rem 0.4rem',
                              borderRadius: '4px',
                              backgroundColor: 'rgba(30, 41, 59, 0.8)',
                              color: '#94a3b8',
                              textTransform: 'uppercase',
                              fontWeight: 600,
                            }}
                          >
                            {evt.action}
                          </span>
                        )}
                        <span>{evt.payload_summary || 'No payload details provided'}</span>
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
