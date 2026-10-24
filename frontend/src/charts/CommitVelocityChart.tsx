import React from 'react';
import { TimelinePoint } from '../types';

interface CommitVelocityChartProps {
  timeline: TimelinePoint[];
  loading?: boolean;
}

export const CommitVelocityChart: React.FC<CommitVelocityChartProps> = ({ timeline, loading }) => {
  if (loading) {
    return (
      <div style={{ height: '240px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
        Loading commit velocity metrics...
      </div>
    );
  }

  if (!timeline || timeline.length === 0) {
    return (
      <div style={{ height: '240px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
        No commit velocity data available.
      </div>
    );
  }

  const maxCommits = Math.max(...timeline.map((p) => p.commit_count), 1);

  return (
    <div
      role="region"
      aria-label="Commit Velocity Chart"
      style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '8px',
        padding: '1.25rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Daily Commit Velocity</h3>
        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Rolling 30-Day Window</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.75rem', height: '180px', paddingTop: '1rem' }}>
        {timeline.map((pt, idx) => {
          const heightPercent = (pt.commit_count / maxCommits) * 100;
          return (
            <div
              key={idx}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                height: '100%',
                justifyContent: 'flex-end',
              }}
            >
              <span style={{ fontSize: '0.7rem', color: '#38bdf8', marginBottom: '0.25rem' }}>
                {pt.commit_count}
              </span>
              <div
                tabIndex={0}
                role="img"
                aria-label={`${pt.commit_count} commits on ${new Date(pt.timestamp).toLocaleDateString()}`}
                style={{
                  width: '100%',
                  height: `${Math.max(heightPercent, 5)}%`,
                  backgroundColor: '#38bdf8',
                  borderRadius: '4px 4px 0 0',
                  transition: 'height 0.3s ease',
                  cursor: 'pointer',
                }}
              />
              <span style={{ fontSize: '0.65rem', color: '#94a3b8', marginTop: '0.5rem', whiteSpace: 'nowrap' }}>
                {new Date(pt.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
