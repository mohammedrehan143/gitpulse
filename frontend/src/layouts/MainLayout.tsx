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
        backgroundColor: '#090d16',
        color: '#f8fafc',
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        position: 'relative',
        overflowX: 'hidden',
      }}
    >
      {/* Ambient background glows */}
      <div
        style={{
          position: 'fixed',
          top: '-150px',
          left: '10%',
          width: '500px',
          height: '500px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(56, 189, 248, 0.05) 0%, transparent 70%)',
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
          background: 'radial-gradient(circle, rgba(168, 85, 247, 0.04) 0%, transparent 70%)',
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
          borderTop: '1px solid rgba(51, 65, 85, 0.5)',
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          fontSize: '0.8rem',
          color: '#64748b',
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
              backgroundColor: '#10b981',
              boxShadow: '0 0 6px #10b981',
            }}
          />
          <span>
            GitPulse Engineering Intelligence Platform • Multi-Agent System (L0 Master Orchestrator)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Activity size={13} style={{ color: '#38bdf8' }} /> Render FastAPI Backend
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <ShieldCheck size={13} style={{ color: '#34d399' }} /> Vercel Edge Frontend
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Terminal size={13} style={{ color: '#c084fc' }} /> Groq AI Insights
          </span>
        </div>
      </footer>
    </div>
  );
};
