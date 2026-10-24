import React from 'react';

interface MetricsCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export const MetricsCard: React.FC<MetricsCardProps> = ({
  label,
  value,
  subtext,
  trend = 'neutral',
}) => {
  const trendColor = trend === 'up' ? '#34d399' : trend === 'down' ? '#f87171' : '#94a3b8';

  return (
    <div
      role="region"
      aria-label={label}
      style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '8px',
        padding: '1.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
      }}
    >
      <span style={{ fontSize: '0.875rem', color: '#94a3b8', fontWeight: 500 }}>
        {label}
      </span>
      <div style={{ fontSize: '1.875rem', fontWeight: 700, color: '#f8fafc' }}>
        {value}
      </div>
      {subtext && (
        <span style={{ fontSize: '0.75rem', color: trendColor }}>
          {subtext}
        </span>
      )}
    </div>
  );
};
