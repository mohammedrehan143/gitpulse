import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Clock, Tag } from 'lucide-react';
import { IssueItem } from '../types';
import { fetchRepositoryIssues } from '../services/api';

interface IssuesTableProps {
  owner: string;
  repo: string;
}

export const IssuesTable: React.FC<IssuesTableProps> = ({ owner, repo }) => {
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('all');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchRepositoryIssues(owner, repo, filter, 30, 0)
      .then((res) => {
        setIssues(res.issues);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load issues');
        setLoading(false);
      });
  }, [owner, repo, filter]);

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
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} color="#dc2626" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
            Issues ({issues.length})
          </h3>
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          {(['all', 'open', 'closed'] as const).map((st) => (
            <button
              key={st}
              onClick={() => setFilter(st)}
              style={{
                padding: '4px 10px',
                fontSize: '12px',
                fontWeight: 600,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: filter === st ? '#dc2626' : '#1c1c1f',
                color: filter === st ? '#ffffff' : '#a1a1aa',
              }}
            >
              {st.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div style={{ color: '#fca5a5', padding: '12px', backgroundColor: 'rgba(239,68,68,0.1)', borderRadius: '6px' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ color: '#71717a', padding: '24px', textAlign: 'center' }}>Loading issues...</div>
      ) : issues.length === 0 ? (
        <div style={{ color: '#71717a', padding: '24px', textAlign: 'center' }}>No issues found.</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #27272a', color: '#71717a', textAlign: 'left' }}>
                <th style={{ padding: '8px' }}>#</th>
                <th style={{ padding: '8px' }}>Title</th>
                <th style={{ padding: '8px' }}>Author</th>
                <th style={{ padding: '8px' }}>Status</th>
                <th style={{ padding: '8px' }}>Labels</th>
                <th style={{ padding: '8px' }}>Created</th>
              </tr>
            </thead>
            <tbody>
              {issues.map((iss) => {
                const isOpen = iss.state === 'open';
                return (
                  <tr key={iss.id} style={{ borderBottom: '1px solid #1c1c1f' }}>
                    <td style={{ padding: '10px 8px', color: '#71717a', fontWeight: 600 }}>#{iss.number}</td>
                    <td style={{ padding: '10px 8px', color: '#f8fafc', fontWeight: 500, maxWidth: '350px' }}>
                      {iss.title}
                    </td>
                    <td style={{ padding: '10px 8px', color: '#a1a1aa' }}>{iss.author_login}</td>
                    <td style={{ padding: '10px 8px' }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '2px 8px',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: 700,
                          backgroundColor: isOpen ? 'rgba(34, 197, 94, 0.15)' : 'rgba(168, 85, 247, 0.15)',
                          color: isOpen ? '#4ade80' : '#c084fc',
                        }}
                      >
                        {isOpen ? <Clock size={12} /> : <CheckCircle size={12} />}
                        {isOpen ? 'Open' : 'Closed'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {iss.labels.map((lbl) => (
                          <span
                            key={lbl}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '2px',
                              padding: '1px 6px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              backgroundColor: '#27272a',
                              color: '#d4d4d8',
                            }}
                          >
                            <Tag size={10} />
                            {lbl}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td style={{ padding: '10px 8px', color: '#71717a', fontSize: '12px' }}>
                      {new Date(iss.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
