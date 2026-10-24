import React from 'react';
import { Header } from '../components/Header';

interface MainLayoutProps {
  children: React.ReactNode;
  currentRepo?: string;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  currentRepo = 'apache/spark',
}) => {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header currentRepo={currentRepo} />
      <main style={{ flex: 1, padding: '2rem', maxWidth: '1400px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
        {children}
      </main>
      <footer
        style={{
          padding: '1.5rem',
          textAlign: 'center',
          borderTop: '1px solid #334155',
          fontSize: '0.875rem',
          color: '#64748b',
          backgroundColor: '#0f172a',
        }}
      >
        GitPulse Analytics Platform — Hierarchical Multi-Agent Architecture
      </footer>
    </div>
  );
};
