import React, { useState } from 'react';
import { GitPullRequest } from 'lucide-react';
import { TimelinePoint } from '../types';

interface ActivityChartProps {
  timeline: TimelinePoint[];
}

export const ActivityChart: React.FC<ActivityChartProps> = ({ timeline }) => {
  const [hoveredPoint, setHoveredPoint] = useState<TimelinePoint | null>(null);

  if (!timeline || timeline.length === 0) {
    return (
      <div
        role="region"
        aria-label="PR Throughput Chart"
        style={{
          height: '280px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#94a3b8',
          backgroundColor: 'rgba(15, 23, 42, 0.75)',
          borderRadius: '12px',
          border: '1px solid rgba(148, 163, 184, 0.15)',
        }}
      >
        No PR activity recorded.
      </div>
    );
  }

  const totalOpened = timeline.reduce((acc, p) => acc + p.pr_opened_count, 0);
  const totalMerged = timeline.reduce((acc, p) => acc + p.pr_merged_count, 0);
  const clearanceRate = totalOpened > 0 ? Math.round((totalMerged / totalOpened) * 100) : 100;
  const maxPR = Math.max(...timeline.map((p) => Math.max(p.pr_opened_count, p.pr_merged_count)), 1);

  return (
    <div
      role="region"
      aria-label="PR Throughput Chart"
      style={{
        backgroundColor: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(8px)',
        border: '1px solid rgba(148, 163, 184, 0.15)',
        borderRadius: '12px',
        padding: '1.25rem',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
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
              backgroundColor: 'rgba(52, 211, 153, 0.12)',
              color: '#34d399',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <GitPullRequest size={15} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>
              Pull Request Throughput
            </h3>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              PR Clearance: <strong style={{ color: '#34d399' }}>{clearanceRate}%</strong>
            </span>
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: '0.85rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.72rem', color: '#94a3b8' }}>
            <div style={{ width: '8px', height: '8px', backgroundColor: '#38bdf8', borderRadius: '2px' }} />
            <span>Opened ({totalOpened})</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.72rem', color: '#94a3b8' }}>
            <div style={{ width: '8px', height: '8px', backgroundColor: '#34d399', borderRadius: '2px' }} />
            <span>Merged ({totalMerged})</span>
          </div>
        </div>
      </div>

      {/* Hover tooltip banner */}
      <div
        style={{
          minHeight: '22px',
          fontSize: '0.75rem',
          color: hoveredPoint ? '#e2e8f0' : '#64748b',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          padding: '0.15rem 0.5rem',
          backgroundColor: hoveredPoint ? 'rgba(30, 41, 59, 0.8)' : 'transparent',
          borderRadius: '4px',
        }}
      >
        {hoveredPoint ? (
          <>
            <span>Date: <strong style={{ color: '#f8fafc' }}>{new Date(hoveredPoint.timestamp).toLocaleDateString()}</strong></span>
            <span>PRs Opened: <strong style={{ color: '#38bdf8' }}>{hoveredPoint.pr_opened_count}</strong></span>
            <span>PRs Merged: <strong style={{ color: '#34d399' }}>{hoveredPoint.pr_merged_count}</strong></span>
          </>
        ) : (
          <span>Hover to inspect PR throughput metrics</span>
        )}
      </div>

      {/* Dual Bar Visualizer */}
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
          const openedH = (pt.pr_opened_count / maxPR) * 100;
          const mergedH = (pt.pr_merged_count / maxPR) * 100;
          const isHovered = hoveredPoint?.timestamp === pt.timestamp;

          return (
            <div
              key={idx}
              onMouseEnter={() => setHoveredPoint(pt)}
              onMouseLeave={() => setHoveredPoint(null)}
              style={{
                flex: 1,
                display: 'flex',
                gap: '2px',
                alignItems: 'flex-end',
                height: '100%',
                position: 'relative',
                cursor: 'pointer',
              }}
            >
              {/* Opened Bar */}
              <div
                style={{
                  flex: 1,
                  height: `${Math.max(openedH, 4)}%`,
                  background: isHovered
                    ? '#38bdf8'
                    : 'linear-gradient(180deg, rgba(56, 189, 248, 0.85) 0%, rgba(2, 132, 199, 0.6) 100%)',
                  borderRadius: '2px 2px 0 0',
                  boxShadow: isHovered ? '0 0 8px rgba(56, 189, 248, 0.5)' : 'none',
                  transition: 'height 0.2s',
                }}
                title={`Opened: ${pt.pr_opened_count}`}
              />

              {/* Merged Bar */}
              <div
                style={{
                  flex: 1,
                  height: `${Math.max(mergedH, 4)}%`,
                  background: isHovered
                    ? '#34d399'
                    : 'linear-gradient(180deg, rgba(52, 211, 153, 0.85) 0%, rgba(5, 150, 105, 0.6) 100%)',
                  borderRadius: '2px 2px 0 0',
                  boxShadow: isHovered ? '0 0 8px rgba(52, 211, 153, 0.5)' : 'none',
                  transition: 'height 0.2s',
                }}
                title={`Merged: ${pt.pr_merged_count}`}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};
