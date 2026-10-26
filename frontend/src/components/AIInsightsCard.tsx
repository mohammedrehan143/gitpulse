import React, { useState } from 'react';
import { Sparkles, Copy, Check, RefreshCw, Cpu, Bot, ChevronDown, ChevronUp } from 'lucide-react';
import { AIInsightsResponse } from '../types';

interface AIInsightsCardProps {
  insights: AIInsightsResponse | null;
  loading: boolean;
  error: string | null;
  onGenerate: () => void;
  repoFullName: string;
}

export const AIInsightsCard: React.FC<AIInsightsCardProps> = ({
  insights,
  loading,
  error,
  onGenerate,
  repoFullName,
}) => {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const handleCopy = () => {
    if (insights?.insights) {
      navigator.clipboard.writeText(insights.insights);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Basic markdown parser for clean display of bolding, bullet points and sections
  const renderFormattedInsights = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return <div key={idx} style={{ height: '0.6rem' }} />;
      }

      // Headers (e.g. ### Header or **Header**)
      if (trimmed.startsWith('###') || trimmed.startsWith('##')) {
        const cleanHeader = trimmed.replace(/^#+\s*/, '');
        return (
          <h4
            key={idx}
            style={{
              fontSize: '0.95rem',
              fontWeight: 700,
              color: '#38bdf8',
              margin: '0.75rem 0 0.35rem 0',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            {cleanHeader}
          </h4>
        );
      }

      // Bullet points
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        const content = trimmed.substring(2);
        return (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.5rem',
              margin: '0.25rem 0',
              fontSize: '0.875rem',
              color: '#e2e8f0',
              lineHeight: 1.5,
            }}
          >
            <span style={{ color: '#06b6d4', marginTop: '0.15rem' }}>•</span>
            <span>{content}</span>
          </div>
        );
      }

      // Table lines
      if (trimmed.startsWith('|')) {
        const cols = trimmed.split('|').filter((c) => c.trim().length > 0);
        if (cols.some((c) => c.includes('---'))) {
          return null; // separator
        }
        return (
          <div
            key={idx}
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${cols.length}, 1fr)`,
              gap: '0.5rem',
              padding: '0.35rem 0.5rem',
              backgroundColor: 'rgba(30, 41, 59, 0.5)',
              borderRadius: '4px',
              margin: '0.2rem 0',
              fontSize: '0.8rem',
              color: '#cbd5e1',
            }}
          >
            {cols.map((col, cIdx) => (
              <span key={cIdx} style={{ fontWeight: cIdx === 0 ? 600 : 400 }}>
                {col.trim()}
              </span>
            ))}
          </div>
        );
      }

      return (
        <p
          key={idx}
          style={{
            margin: '0.35rem 0',
            fontSize: '0.875rem',
            color: '#cbd5e1',
            lineHeight: 1.55,
          }}
        >
          {trimmed}
        </p>
      );
    });
  };

  return (
    <div
      style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.75) 100%)',
        border: '1px solid rgba(56, 189, 248, 0.25)',
        borderRadius: '12px',
        padding: '1.5rem',
        marginBottom: '2rem',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.35)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Ambient background glow */}
      <div
        style={{
          position: 'absolute',
          top: '-60px',
          right: '-60px',
          width: '180px',
          height: '180px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(6, 182, 212, 0.15) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: '0 0 15px rgba(6, 182, 212, 0.4)',
            }}
          >
            <Sparkles size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc' }}>
                Engineering Velocity Copilot
              </h3>
              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  padding: '0.15rem 0.5rem',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                <Bot size={11} /> Groq AI
              </span>
            </div>
            <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
              Real-time engineering intelligence, PR turnaround diagnosis & bottleneck insights for{' '}
              <strong style={{ color: '#38bdf8' }}>{repoFullName}</strong>
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {insights && (
            <button
              onClick={handleCopy}
              aria-label="Copy AI Insights"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.45rem 0.75rem',
                fontSize: '0.8rem',
                fontWeight: 500,
                borderRadius: '8px',
                backgroundColor: 'rgba(30, 41, 59, 0.8)',
                color: copied ? '#34d399' : '#cbd5e1',
                border: '1px solid rgba(148, 163, 184, 0.2)',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          )}

          <button
            onClick={onGenerate}
            disabled={loading}
            aria-label="Generate Velocity Insights"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.45rem',
              padding: '0.45rem 0.95rem',
              fontSize: '0.825rem',
              fontWeight: 600,
              borderRadius: '8px',
              background: loading
                ? '#334155'
                : 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)',
              color: '#ffffff',
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              boxShadow: loading ? 'none' : '0 2px 10px rgba(6, 182, 212, 0.3)',
              transition: 'all 0.2s',
            }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            {loading ? 'Synthesizing...' : insights ? 'Refresh Insights' : 'Generate Insights'}
          </button>

          {insights && (
            <button
              onClick={() => setExpanded(!expanded)}
              aria-label={expanded ? 'Collapse insights' : 'Expand insights'}
              style={{
                padding: '0.45rem',
                borderRadius: '8px',
                backgroundColor: 'rgba(30, 41, 59, 0.8)',
                color: '#94a3b8',
                border: '1px solid rgba(148, 163, 184, 0.2)',
                cursor: 'pointer',
              }}
            >
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div
          role="alert"
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '8px',
            padding: '0.75rem 1rem',
            color: '#fca5a5',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <span>Error generating insights: {error}</span>
        </div>
      )}

      {loading && (
        <div
          style={{
            padding: '2rem',
            textAlign: 'center',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            borderRadius: '8px',
            border: '1px dashed rgba(56, 189, 248, 0.3)',
          }}
        >
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.6rem',
              fontSize: '0.9rem',
              color: '#38bdf8',
            }}
          >
            <Cpu size={18} className="animate-pulse" />
            <span>Consulting Groq AI (`openai/gpt-oss-120b`)... Analyzing commit velocity and code churn</span>
          </div>
        </div>
      )}

      {!loading && !insights && !error && (
        <div
          style={{
            padding: '1.5rem',
            backgroundColor: 'rgba(15, 23, 42, 0.4)',
            borderRadius: '8px',
            border: '1px dashed rgba(148, 163, 184, 0.2)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div>
            <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0' }}>
              No velocity insights generated yet for this repository
            </div>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.2rem' }}>
              Click "Generate Insights" to run an automated architectural audit of recent PR throughput, author distribution, and code churn.
            </div>
          </div>
          <button
            onClick={onGenerate}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.45rem 0.85rem',
              fontSize: '0.8rem',
              fontWeight: 600,
              borderRadius: '6px',
              backgroundColor: '#0284c7',
              color: '#ffffff',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <Sparkles size={14} /> Analyze Velocity
          </button>
        </div>
      )}

      {!loading && insights && expanded && (
        <div
          style={{
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(148, 163, 184, 0.15)',
            borderRadius: '8px',
            padding: '1.25rem',
            maxHeight: '400px',
            overflowY: 'auto',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '0.75rem',
              paddingBottom: '0.5rem',
              borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
            }}
          >
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Bot size={12} /> Model: <strong style={{ color: '#e2e8f0' }}>{insights.model}</strong>
            </span>
            <span style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>
              Live Analysis Complete
            </span>
          </div>
          <div>{renderFormattedInsights(insights.insights)}</div>
        </div>
      )}
    </div>
  );
};
