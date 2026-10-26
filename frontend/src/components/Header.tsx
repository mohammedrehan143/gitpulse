import React from 'react';
import { Radio, ExternalLink, RefreshCw, Terminal, Layers } from 'lucide-react';

interface HeaderProps {
  currentRepo: string;
  wsConnected?: boolean;
  onRefreshAll?: () => void;
  isRefreshing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentRepo,
  wsConnected = true,
  onRefreshAll,
  isRefreshing = false,
}) => {
  return (
    <header
      role="banner"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.9rem 2rem',
        backgroundColor: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(51, 65, 85, 0.7)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Brand & Platform Tag */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        <div
          style={{
            width: '34px',
            height: '34px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '0.9rem',
            color: '#ffffff',
            boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)',
          }}
        >
          GP
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h1 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.02em' }}>
              GitPulse
            </h1>
            <span
              style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                letterSpacing: '0.05em',
                padding: '0.15rem 0.5rem',
                borderRadius: '9999px',
                background: 'linear-gradient(135deg, #0369a1 0%, #0284c7 100%)',
                color: '#ffffff',
                textTransform: 'uppercase',
              }}
            >
              Intelligence
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
            GitHub Activity Analytics & Velocity Platform
          </span>
        </div>
      </div>

      {/* Center/Right Metrics & Live Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        {/* Real-time WebSocket Stream Indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            padding: '0.35rem 0.75rem',
            borderRadius: '9999px',
            backgroundColor: wsConnected ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
            border: `1px solid ${wsConnected ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            fontSize: '0.75rem',
            fontWeight: 600,
            color: wsConnected ? '#34d399' : '#f87171',
          }}
          title={wsConnected ? 'Subscribed to live repository event stream' : 'WebSocket stream disconnected'}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: wsConnected ? '#10b981' : '#ef4444',
              boxShadow: wsConnected ? '0 0 8px #10b981' : 'none',
              display: 'inline-block',
            }}
          />
          <Radio size={12} />
          <span>{wsConnected ? 'Live Feed Connected' : 'Stream Paused'}</span>
        </div>

        {/* Current Active Repo Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            padding: '0.35rem 0.75rem',
            borderRadius: '8px',
            backgroundColor: 'rgba(30, 41, 59, 0.7)',
            border: '1px solid rgba(148, 163, 184, 0.2)',
            fontSize: '0.8rem',
          }}
        >
          <Layers size={13} style={{ color: '#38bdf8' }} />
          <span style={{ color: '#94a3b8' }}>Active:</span>
          <strong style={{ color: '#f8fafc' }}>{currentRepo}</strong>
        </div>

        {/* API Docs Button */}
        <a
          href="/docs"
          target="_blank"
          rel="noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.35rem 0.65rem',
            borderRadius: '6px',
            backgroundColor: 'rgba(30, 41, 59, 0.6)',
            color: '#cbd5e1',
            border: '1px solid rgba(148, 163, 184, 0.2)',
            fontSize: '0.75rem',
            fontWeight: 500,
            textDecoration: 'none',
            transition: 'all 0.2s',
          }}
          title="Open FastAPI Swagger Interactive Documentation"
        >
          <Terminal size={12} />
          <span>Swagger Docs</span>
          <ExternalLink size={10} style={{ color: '#64748b' }} />
        </a>

        {/* Refresh Trigger */}
        {onRefreshAll && (
          <button
            onClick={onRefreshAll}
            disabled={isRefreshing}
            aria-label="Refresh All Analytics"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '0.35rem 0.75rem',
              borderRadius: '6px',
              backgroundColor: '#0284c7',
              color: '#ffffff',
              border: 'none',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: isRefreshing ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
            }}
          >
            <RefreshCw size={12} style={{ animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }} />
            <span>{isRefreshing ? 'Syncing...' : 'Sync Data'}</span>
          </button>
        )}
      </div>
    </header>
  );
};
