import React from 'react';
import { Header } from '../components/Header';
import { ShieldCheck, Activity, Terminal } from 'lucide-react';

interface MainLayoutProps {
  children: React.ReactNode;
  currentRepo?: string;
  wsConnected?: boolean;
  onRefreshAll?: () => void;
  isRefreshing?: boolean;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  currentRepo = 'apache/spark',
  wsConnected = true,
  onRefreshAll,
  isRefreshing = false,
}) => {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#050505',
        color: '#ffffff',
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        position: 'relative',
        overflowX: 'hidden',
      }}
    >
      {/* Ambient background subtle red glow */}
      <div
        style={{
          position: 'fixed',
          top: '-150px',
          left: '10%',
          width: '500px',
          height: '500px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(220, 38, 38, 0.04) 0%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />
      <div
        style={{
          position: 'fixed',
          bottom: '10%',
          right: '5%',
          width: '600px',
          height: '600px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(239, 68, 68, 0.03) 0%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      <Header
        currentRepo={currentRepo}
        wsConnected={wsConnected}
        onRefreshAll={onRefreshAll}
        isRefreshing={isRefreshing}
      />

      <main
        style={{
          flex: 1,
          padding: '2rem',
          maxWidth: '1440px',
          margin: '0 auto',
          width: '100%',
          boxSizing: 'border-box',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {children}
      </main>

      {/* Footer */}
      <footer
        style={{
          padding: '1.75rem 2rem',
          borderTop: '1px solid #1f1f1f',
          backgroundColor: '#0a0a0a',
          fontSize: '0.8rem',
          color: '#71717a',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#ef4444',
            }}
          />
          <span style={{ color: '#d4d4d8' }}>
            GitPulse Engineering Intelligence Platform • Multi-Agent System (L0 Master Orchestrator)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#a1a1aa' }}>
            <Activity size={13} style={{ color: '#ef4444' }} /> Render FastAPI Backend
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#a1a1aa' }}>
            <ShieldCheck size={13} style={{ color: '#ffffff' }} /> Vercel Edge Frontend
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#a1a1aa' }}>
            <Terminal size={13} style={{ color: '#f87171' }} /> Groq AI Insights
          </span>
        </div>
      </footer>
    </div>
  );
};
