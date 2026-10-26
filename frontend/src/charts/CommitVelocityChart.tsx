import React, { useState } from 'react';
import { GitCommit, TrendingUp } from 'lucide-react';
import { TimelinePoint } from '../types';

interface CommitVelocityChartProps {
  timeline: TimelinePoint[];
  loading?: boolean;
}

export const CommitVelocityChart: React.FC<CommitVelocityChartProps> = ({ timeline, loading }) => {
  const [hoveredPoint, setHoveredPoint] = useState<TimelinePoint | null>(null);

  if (loading) {
    return (
      <div
        role="region"
        aria-label="Commit Velocity Chart"
        style={{
          height: '280px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#a1a1aa',
          backgroundColor: '#121212',
          borderRadius: '12px',
          border: '1px solid #27272a',
        }}
      >
        Loading commit velocity metrics...
      </div>
    );
  }

  if (!timeline || timeline.length === 0) {
    return (
      <div
        role="region"
        aria-label="Commit Velocity Chart"
        style={{
          height: '280px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#a1a1aa',
          backgroundColor: '#121212',
          borderRadius: '12px',
          border: '1px solid #27272a',
        }}
      >
        No commit velocity data available.
      </div>
    );
  }

  const maxCommits = Math.max(...timeline.map((p) => p.commit_count), 1);
  const totalCommits = timeline.reduce((acc, p) => acc + p.commit_count, 0);
  const avgCommits = Math.round(totalCommits / timeline.length);
  const peakDay = timeline.reduce((max, p) => (p.commit_count > max.commit_count ? p : max), timeline[0]);

  return (
    <div
      role="region"
      aria-label="Commit Velocity Chart"
      style={{
        backgroundColor: '#121212',
        border: '1px solid #27272a',
        borderRadius: '12px',
        padding: '1.25rem',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: '300px',
        boxSizing: 'border-box',
      }}
    >
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div
            style={{
              width: '26px',
              height: '26px',
              borderRadius: '6px',
              backgroundColor: 'rgba(220, 38, 38, 0.12)',
              color: '#ef4444',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <GitCommit size={15} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#ffffff' }}>
              Daily Commit Velocity
            </h3>
            <span style={{ fontSize: '0.72rem', color: '#a1a1aa' }}>
              Avg: <strong style={{ color: '#ef4444' }}>{avgCommits}</strong> commits/day
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span
            style={{
              fontSize: '0.7rem',
              fontWeight: 600,
              padding: '0.2rem 0.5rem',
              borderRadius: '9999px',
              backgroundColor: '#18181b',
              border: '1px solid #ef4444',
              color: '#ef4444',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            <TrendingUp size={11} /> Peak: {peakDay.commit_count}
          </span>
        </div>
      </div>

      {/* Hover tooltip banner */}
      <div
        style={{
          minHeight: '22px',
          fontSize: '0.75rem',
          color: hoveredPoint ? '#ffffff' : '#71717a',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          padding: '0.15rem 0.5rem',
          backgroundColor: hoveredPoint ? '#18181b' : 'transparent',
          borderRadius: '4px',
        }}
      >
        {hoveredPoint ? (
          <>
            <span>Date: <strong style={{ color: '#ef4444' }}>{new Date(hoveredPoint.timestamp).toLocaleDateString()}</strong></span>
            <span>Commits: <strong style={{ color: '#ffffff' }}>{hoveredPoint.commit_count}</strong></span>
            <span>Authors: <strong style={{ color: '#ffffff' }}>{hoveredPoint.active_authors}</strong></span>
            <span>Net lines: <strong style={{ color: '#ffffff' }}>+{hoveredPoint.net_lines}</strong></span>
          </>
        ) : (
          <span>Hover over any bar to view daily commit breakdown</span>
        )}
      </div>

      {/* Bar visualizer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: timeline.length > 20 ? '4px' : '8px',
          height: '170px',
          paddingTop: '0.5rem',
        }}
      >
        {timeline.map((pt, idx) => {
          const heightPercent = (pt.commit_count / maxCommits) * 100;
          const isHovered = hoveredPoint?.timestamp === pt.timestamp;

          return (
            <div
              key={idx}
              onMouseEnter={() => setHoveredPoint(pt)}
              onMouseLeave={() => setHoveredPoint(null)}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                height: '100%',
                justifyContent: 'flex-end',
                position: 'relative',
              }}
            >
              <div
                tabIndex={0}
                role="img"
                aria-label={`${pt.commit_count} commits on ${new Date(pt.timestamp).toLocaleDateString()}`}
                style={{
                  width: '100%',
                  height: `${Math.max(heightPercent, 6)}%`,
                  background: isHovered
                    ? '#ef4444'
                    : 'linear-gradient(180deg, #dc2626 0%, #991b1b 100%)',
                  borderRadius: '4px 4px 0 0',
                  boxShadow: 'none',
                  transition: 'height 0.2s ease, background 0.15s',
                  cursor: 'pointer',
                }}
              />
              {idx % Math.ceil(timeline.length / 7) === 0 && (
                <span
                  style={{
                    fontSize: '0.62rem',
                    color: '#71717a',
                    marginTop: '0.35rem',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {new Date(pt.timestamp).toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' })}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
