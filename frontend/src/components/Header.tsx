import React from 'react';
import { Radio, ExternalLink, RefreshCw, Terminal, Layers, Activity } from 'lucide-react';
import { useKeepAlive } from '../hooks/useKeepAlive';

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
  const { lastPulse, lastPulseAt, isPulsing, triggerPulse } = useKeepAlive();
  return (
    <header
      role="banner"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.9rem 2rem',
        backgroundColor: 'rgba(10, 10, 10, 0.95)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid #1f1f1f',
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
            background: 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '0.9rem',
            color: '#ffffff',
            boxShadow: '0 0 12px rgba(220, 38, 38, 0.3)',
          }}
        >
          GP
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h1 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#ffffff', letterSpacing: '-0.02em' }}>
              GitPulse
            </h1>
            <span
              style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                letterSpacing: '0.05em',
                padding: '0.15rem 0.5rem',
                borderRadius: '4px',
                background: '#18181b',
                border: '1px solid #dc2626',
                color: '#ef4444',
                textTransform: 'uppercase',
              }}
            >
              Intelligence
            </span>
          </div>
          <span style={{ fontSize: '0.72rem', color: '#a1a1aa' }}>
            GitHub Activity Analytics & Velocity Platform
          </span>
        </div>
      </div>

      {/* Center/Right Metrics & Live Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        {/* Real-time WebSocket Stream Indicator (Clean, No Pulsing, Red/White Theme) */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            padding: '0.35rem 0.75rem',
            borderRadius: '6px',
            backgroundColor: '#18181b',
            border: '1px solid #27272a',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: '#ffffff',
          }}
          title={wsConnected ? 'Subscribed to live repository event stream' : 'WebSocket stream disconnected'}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: wsConnected ? '#ef4444' : '#71717a',
              display: 'inline-block',
            }}
          />
          <Radio size={12} color="#ef4444" />
          <span>{wsConnected ? 'Live Connected' : 'Stream Paused'}</span>
        </div>

        {/* Autonomous 5-Min Keep-Alive Heartbeat Pulse */}
        <div
          onClick={() => triggerPulse(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            padding: '0.35rem 0.75rem',
            borderRadius: '6px',
            backgroundColor: '#18181b',
            border: '1px solid #27272a',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: '#ffffff',
            cursor: 'pointer',
            userSelect: 'none',
          }}
          title={`GitPulse 5-minute autonomous keep-alive pulse.\nLast pulse: ${lastPulseAt ? lastPulseAt.toLocaleTimeString() : 'Initializing'}\nDatabase status: ${lastPulse?.database || 'Connected'}\nClick to trigger instant database sync pulse.`}
        >
          <Activity size={12} color="#ef4444" />
          <span>{isPulsing ? 'Pulsing...' : 'Pulse: 5m Active'}</span>
        </div>

        {/* Current Active Repo Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            padding: '0.35rem 0.75rem',
            borderRadius: '6px',
            backgroundColor: '#141414',
            border: '1px solid #27272a',
            fontSize: '0.8rem',
          }}
        >
          <Layers size={13} style={{ color: '#ef4444' }} />
          <span style={{ color: '#a1a1aa' }}>Active:</span>
          <strong style={{ color: '#ffffff' }}>{currentRepo}</strong>
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
            backgroundColor: '#18181b',
            color: '#ffffff',
            border: '1px solid #27272a',
            fontSize: '0.75rem',
            fontWeight: 500,
            textDecoration: 'none',
            transition: 'all 0.2s',
          }}
          title="Open FastAPI Swagger Interactive Documentation"
        >
          <Terminal size={12} color="#ef4444" />
          <span>Swagger Docs</span>
          <ExternalLink size={10} style={{ color: '#71717a' }} />
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
              backgroundColor: '#dc2626',
              color: '#ffffff',
              border: 'none',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: isRefreshing ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
            }}
          >
            <RefreshCw size={12} />
            <span>{isRefreshing ? 'Syncing...' : 'Sync Data'}</span>
          </button>
        )}
      </div>
    </header>
  );
};
