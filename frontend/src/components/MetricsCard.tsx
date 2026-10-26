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

  const trendColor = isUp ? '#34d399' : isDown ? '#f87171' : '#94a3b8';
  const trendBg = isUp
    ? 'rgba(52, 211, 153, 0.12)'
    : isDown
    ? 'rgba(248, 113, 113, 0.12)'
    : 'rgba(148, 163, 184, 0.1)';

  return (
    <div
      role="region"
      aria-label={label}
      style={{
        backgroundColor: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(8px)',
        border: '1px solid rgba(148, 163, 184, 0.15)',
        borderRadius: '12px',
        padding: '1.25rem',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        position: 'relative',
        overflow: 'hidden',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
        transition: 'border-color 0.2s, transform 0.2s',
      }}
    >
      {/* Top row: label + icon */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '0.825rem', color: '#94a3b8', fontWeight: 600, letterSpacing: '0.01em' }}>
          {label}
        </span>
        {icon && (
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: 'rgba(56, 189, 248, 0.1)',
              color: '#38bdf8',
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
          color: '#f8fafc',
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
              fontSize: '0.72rem',
              fontWeight: 600,
            }}
          >
            {isUp ? <ArrowUpRight size={12} /> : isDown ? <ArrowDownRight size={12} /> : <Minus size={12} />}
            <span>{subtext}</span>
          </div>
        )}
        {badge && (
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
            {badge}
          </span>
        )}
      </div>
    </div>
  );
};
