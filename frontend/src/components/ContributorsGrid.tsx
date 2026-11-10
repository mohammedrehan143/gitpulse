import React, { useState, useEffect } from 'react';
import { Users, GitCommit, GitPullRequest, AlertCircle } from 'lucide-react';
import { ContributorItem } from '../types';
import { fetchRepositoryContributors } from '../services/api';

interface ContributorsGridProps {
  owner: string;
  repo: string;
}

export const ContributorsGrid: React.FC<ContributorsGridProps> = ({ owner, repo }) => {
  const [contributors, setContributors] = useState<ContributorItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchRepositoryContributors(owner, repo)
      .then((res) => {
        setContributors(res.contributors);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load contributors');
        setLoading(false);
      });
  }, [owner, repo]);

  return (
    <div
      style={{
        backgroundColor: '#121212',
        border: '1px solid #27272a',
        borderRadius: '12px',
        padding: '1.25rem',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1.25rem' }}>
        <Users size={18} color="#dc2626" />
        <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
          Active Contributors ({contributors.length})
        </h3>
      </div>

      {error && (
        <div style={{ color: '#fca5a5', padding: '12px', backgroundColor: 'rgba(239,68,68,0.1)', borderRadius: '6px' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ color: '#71717a', padding: '24px', textAlign: 'center' }}>Loading contributors...</div>
      ) : contributors.length === 0 ? (
        <div style={{ color: '#71717a', padding: '24px', textAlign: 'center' }}>No contributors tracked yet.</div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
            gap: '12px',
          }}
        >
          {contributors.map((c) => (
            <div
              key={c.id}
              style={{
                backgroundColor: '#18181b',
                border: '1px solid #27272a',
                borderRadius: '8px',
                padding: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              {c.avatar_url ? (
                <img
                  src={c.avatar_url}
                  alt={c.login}
                  style={{ width: '40px', height: '40px', borderRadius: '50%', border: '1px solid #3f3f46' }}
                />
              ) : (
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    backgroundColor: '#27272a',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#ffffff',
                    fontWeight: 700,
                  }}
                >
                  {c.login.charAt(0).toUpperCase()}
                </div>
              )}

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {c.name || c.login}
                </div>
                <div style={{ color: '#71717a', fontSize: '11px' }}>@{c.login}</div>
                <div style={{ display: 'flex', gap: '8px', marginTop: '6px', fontSize: '11px', color: '#a1a1aa' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                    <GitCommit size={11} color="#ef4444" /> {c.commits_count}
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                    <GitPullRequest size={11} color="#a855f7" /> {c.prs_count}
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                    <AlertCircle size={11} color="#3b82f6" /> {c.issues_count}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
