import React from 'react';

interface HeaderProps {
  currentRepo: string;
  onRepoChange?: (repo: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ currentRepo }) => {
  return (
    <header
      role="banner"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '1rem 2rem',
        backgroundColor: '#1e293b',
        borderBottom: '1px solid #334155',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div
          style={{
            width: '28px',
            height: '28px',
            borderRadius: '6px',
            backgroundColor: '#38bdf8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            color: '#0f172a',
          }}
        >
          GP
        </div>
        <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>GitPulse</h1>
        <span
          style={{
            fontSize: '0.75rem',
            padding: '0.2rem 0.5rem',
            borderRadius: '9999px',
            backgroundColor: '#0284c7',
            color: '#ffffff',
          }}
        >
          Analytics Platform
        </span>
      </div>
      <div>
        <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Tracking: </span>
        <strong style={{ color: '#f8fafc', fontSize: '0.875rem' }}>{currentRepo}</strong>
      </div>
    </header>
  );
};
