import React from 'react';
import { TimelinePoint } from '../types';

interface ActivityChartProps {
  timeline: TimelinePoint[];
}

export const ActivityChart: React.FC<ActivityChartProps> = ({ timeline }) => {
  return (
    <div
      role="region"
      aria-label="PR Throughput Chart"
      style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '8px',
        padding: '1.25rem',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Pull Request Throughput</h3>
        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Opened vs Merged</span>
      </div>

      <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: '#94a3b8' }}>
          <div style={{ width: '10px', height: '10px', backgroundColor: '#38bdf8', borderRadius: '2px' }} />
          <span>Opened</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: '#94a3b8' }}>
          <div style={{ width: '10px', height: '10px', backgroundColor: '#34d399', borderRadius: '2px' }} />
          <span>Merged</span>
        </div>
      </div>

      <div style={{ height: '160px', display: 'flex', alignItems: 'flex-end', gap: '1rem', paddingTop: '1rem' }}>
        {timeline.map((pt, idx) => (
          <div key={idx} style={{ flex: 1, display: 'flex', gap: '4px', alignItems: 'flex-end', height: '100%' }}>
            <div
              style={{
                flex: 1,
                height: `${Math.min(pt.pr_opened_count * 15, 100)}%`,
                backgroundColor: '#38bdf8',
                borderRadius: '2px',
              }}
              title={`Opened: ${pt.pr_opened_count}`}
            />
            <div
              style={{
                flex: 1,
                height: `${Math.min(pt.pr_merged_count * 15, 100)}%`,
                backgroundColor: '#34d399',
                borderRadius: '2px',
              }}
              title={`Merged: ${pt.pr_merged_count}`}
            />
          </div>
        ))}
      </div>
    </div>
  );
};
