import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface MetricsCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  badge?: string;
}

export const MetricsCard: React.FC<MetricsCardProps> = ({
  label,
  value,
  subtext,
  trend = 'neutral',
  icon,
  badge,
}) => {
  const isUp = trend === 'up';
  const isDown = trend === 'down';

  const trendColor = isUp ? '#ffffff' : isDown ? '#ef4444' : '#a1a1aa';
  const trendBg = isUp
    ? 'rgba(255, 255, 255, 0.1)'
    : isDown
    ? 'rgba(239, 68, 68, 0.15)'
    : 'rgba(255, 255, 255, 0.05)';

  return (
    <div
      role="region"
      aria-label={label}
      style={{
        backgroundColor: '#121212',
        border: '1px solid #27272a',
        borderRadius: '12px',
        padding: '1.25rem',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        position: 'relative',
        overflow: 'hidden',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
        transition: 'border-color 0.2s, transform 0.2s',
      }}
    >
      {/* Top row: label + icon */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '0.825rem', color: '#a1a1aa', fontWeight: 600, letterSpacing: '0.01em' }}>
          {label}
        </span>
        {icon && (
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
            {icon}
          </div>
        )}
      </div>

      {/* Main big metric */}
      <div
        style={{
          fontSize: '1.9rem',
          fontWeight: 800,
          color: '#ffffff',
          letterSpacing: '-0.03em',
          margin: '0.2rem 0',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
        }}
      >
        {value}
      </div>

      {/* Subtext and trend pill */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.4rem', flexWrap: 'wrap' }}>
        {subtext && (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.25rem',
              padding: '0.2rem 0.5rem',
              borderRadius: '9999px',
              backgroundColor: trendBg,
              color: trendColor,
              border: `1px solid ${isUp ? '#3f3f46' : isDown ? '#7f1d1d' : '#27272a'}`,
              fontSize: '0.72rem',
              fontWeight: 600,
            }}
          >
            {isUp ? <ArrowUpRight size={12} /> : isDown ? <ArrowDownRight size={12} /> : <Minus size={12} />}
            <span>{subtext}</span>
          </div>
        )}
        {badge && (
          <span style={{ fontSize: '0.7rem', color: '#71717a' }}>
            {badge}
          </span>
        )}
      </div>
    </div>
  );
};
