import React from 'react';
import { EventItem } from '../types';

interface RecentEventsTableProps {
  events: EventItem[];
  loading?: boolean;
}

export const RecentEventsTable: React.FC<RecentEventsTableProps> = ({ events, loading }) => {
  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
        Loading recent repository events...
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
        No recent activity events recorded.
      </div>
    );
  }

  return (
    <div
      style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '8px',
        overflow: 'hidden',
      }}
    >
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
        <thead>
          <tr style={{ backgroundColor: '#0f172a', borderBottom: '1px solid #334155' }}>
            <th style={{ padding: '0.75rem 1rem', fontSize: '0.75rem', color: '#94a3b8' }}>EVENT</th>
            <th style={{ padding: '0.75rem 1rem', fontSize: '0.75rem', color: '#94a3b8' }}>ACTOR</th>
            <th style={{ padding: '0.75rem 1rem', fontSize: '0.75rem', color: '#94a3b8' }}>DETAILS</th>
            <th style={{ padding: '0.75rem 1rem', fontSize: '0.75rem', color: '#94a3b8' }}>TIME</th>
          </tr>
        </thead>
        <tbody>
          {events.map((evt) => (
            <tr key={evt.event_id} style={{ borderBottom: '1px solid #334155' }}>
              <td style={{ padding: '0.75rem 1rem', fontSize: '0.875rem', fontWeight: 600 }}>
                {evt.event_type}
              </td>
              <td style={{ padding: '0.75rem 1rem', fontSize: '0.875rem' }}>{evt.actor}</td>
              <td style={{ padding: '0.75rem 1rem', fontSize: '0.875rem', color: '#cbd5e1' }}>
                {evt.payload_summary || 'No payload details'}
              </td>
              <td style={{ padding: '0.75rem 1rem', fontSize: '0.75rem', color: '#94a3b8' }}>
                {new Date(evt.created_at).toLocaleTimeString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
