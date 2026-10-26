import React, { useState } from 'react';
import { PRReviewDelayInsights, PRReviewPredictResponse } from '../../types';
import { GitPullRequest, Send } from 'lucide-react';

interface PRIntelligenceCardProps {
  insights: PRReviewDelayInsights | null;
  loading: boolean;
  onPredict: (title: string, additions: number, deletions: number, changedFiles: number) => Promise<PRReviewPredictResponse>;
}

export const PRIntelligenceCard: React.FC<PRIntelligenceCardProps> = ({
  insights,
  loading,
  onPredict,
}) => {
  const [prTitle, setPrTitle] = useState('');
  const [additions, setAdditions] = useState(120);
  const [deletions, setDeletions] = useState(30);
  const [changedFiles, setChangedFiles] = useState(4);
  const [prediction, setPrediction] = useState<PRReviewPredictResponse | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [predictError, setPredictError] = useState<string | null>(null);

  const handlePredictSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prTitle.trim()) return;
    setPredicting(true);
    setPredictError(null);
    try {
      const res = await onPredict(prTitle, additions, deletions, changedFiles);
      setPrediction(res);
    } catch (err: unknown) {
      setPredictError(err instanceof Error ? err.message : 'Prediction failed');
    } finally {
      setPredicting(false);
    }
  };

  if (loading) {
    return (
      <div
        style={{
          padding: '24px',
          backgroundColor: '#121212',
          borderRadius: '12px',
          border: '1px solid #27272a',
          color: '#a1a1aa',
          minHeight: '280px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span>Loading PR turnaround factors & correlation data...</span>
      </div>
    );
  }

  const stats = insights?.statistics;
  const training = insights?.training;
  const brackets = stats?.size_brackets || [];
  const correlations = stats?.correlations;
  const censoring = stats?.censoring_stats;

  return (
    <div
      style={{
        padding: '24px',
        backgroundColor: '#121212',
        borderRadius: '12px',
        border: '1px solid #27272a',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <GitPullRequest size={20} color="#ef4444" />
          <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#ffffff' }}>
            Pull-Request First-Review Delay Analysis
          </h3>
          <span
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              backgroundColor: '#18181b',
              color: '#ef4444',
              border: '1px solid #ef4444',
              borderRadius: '9999px',
              fontWeight: 600,
            }}
          >
            Right-Censoring Aware
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '13px', color: '#a1a1aa' }}>
          Evaluates PR size vs turnaround turnaround time, Spearman correlations, and predictive first-review hours
        </p>
      </div>

      {/* Censoring & Median Metrics Strip */}
      {censoring && (
        <div
          style={{
            display: 'flex',
            gap: '16px',
            marginBottom: '16px',
            padding: '10px 16px',
            backgroundColor: '#18181b',
            border: '1px solid #27272a',
            borderRadius: '8px',
            fontSize: '13px',
            color: '#a1a1aa',
            flexWrap: 'wrap',
          }}
        >
          <div>
            Analyzed PRs: <strong style={{ color: '#ffffff' }}>{censoring.total_prs_analyzed}</strong>
          </div>
          <div>
            Reviewed: <strong style={{ color: '#ffffff' }}>{censoring.reviewed_prs}</strong>
          </div>
          <div>
            Unreviewed (Censored): <strong style={{ color: '#ef4444' }}>{censoring.unreviewed_censored_prs} ({censoring.censoring_rate_pct}%)</strong>
          </div>
          {stats?.overall_median_delay_hours !== undefined && (
            <div style={{ marginLeft: 'auto', color: '#ffffff' }}>
              Overall Median First Review: <strong style={{ color: '#ef4444' }}>{stats.overall_median_delay_hours}h</strong>
              {training?.best_model && (
                <span style={{ marginLeft: '8px', fontSize: '11px', color: '#a1a1aa' }}>
                  (Model: {training.best_model})
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Size Bracket Turnaround Grid */}
      {brackets.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontSize: '12px', color: '#a1a1aa', fontWeight: 600, marginBottom: '8px' }}>
            Turnaround by PR Size Bracket:
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
              gap: '10px',
            }}
          >
            {brackets.map((b) => (
              <div
                key={b.bracket}
                style={{
                  padding: '10px 12px',
                  backgroundColor: '#18181b',
                  borderRadius: '6px',
                  border: '1px solid #27272a',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: '11px', color: '#a1a1aa', marginBottom: '4px' }}>{b.bracket}</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: '#ffffff' }}>
                  {b.median_delay_hours}h
                </div>
                <div style={{ fontSize: '10px', color: '#71717a' }}>{b.count} PRs</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Correlation stats summary */}
      {correlations?.total_lines_changed && (
        <div
          style={{
            fontSize: '12px',
            color: '#a1a1aa',
            marginBottom: '16px',
            padding: '8px 12px',
            backgroundColor: '#18181b',
            border: '1px solid #27272a',
            borderRadius: '6px',
          }}
        >
          Lines changed vs Delay Correlation (Spearman ρ):{' '}
          <strong style={{ color: '#ffffff' }}>{correlations.total_lines_changed.spearman_correlation}</strong>{' '}
          (p={correlations.total_lines_changed.p_value},{' '}
          {correlations.total_lines_changed.statistically_significant ? 'Statistically Significant' : 'Not Significant'})
        </div>
      )}

      {/* Interactive Predictor Form */}
      <form onSubmit={handlePredictSubmit} style={{ marginTop: '16px' }}>
        <div style={{ marginBottom: '12px' }}>
          <label style={{ display: 'block', fontSize: '12px', color: '#a1a1aa', marginBottom: '6px', fontWeight: 600 }}>
            Simulate Inbound Pull Request:
          </label>
          <input
            type="text"
            placeholder="e.g., feat(streaming): Add zero-copy Kafka deserializer sink"
            value={prTitle}
            onChange={(e) => setPrTitle(e.target.value)}
            style={{
              width: '100%',
              boxSizing: 'border-box',
              padding: '8px 12px',
              backgroundColor: '#18181b',
              border: '1px solid #27272a',
              borderRadius: '6px',
              color: '#ffffff',
              fontSize: '13px',
              outline: 'none',
              marginBottom: '10px',
            }}
          />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '8px' }}>
            <div>
              <span style={{ fontSize: '11px', color: '#a1a1aa' }}>Additions (+):</span>
              <input
                type="number"
                min="0"
                value={additions}
                onChange={(e) => setAdditions(parseInt(e.target.value) || 0)}
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  padding: '6px 8px',
                  backgroundColor: '#18181b',
                  border: '1px solid #27272a',
                  borderRadius: '6px',
                  color: '#ffffff',
                  fontSize: '12px',
                }}
              />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: '#a1a1aa' }}>Deletions (-):</span>
              <input
                type="number"
                min="0"
                value={deletions}
                onChange={(e) => setDeletions(parseInt(e.target.value) || 0)}
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  padding: '6px 8px',
                  backgroundColor: '#18181b',
                  border: '1px solid #27272a',
                  borderRadius: '6px',
                  color: '#ef4444',
                  fontSize: '12px',
                }}
              />
            </div>
            <div>
              <span style={{ fontSize: '11px', color: '#a1a1aa' }}>Changed Files:</span>
              <input
                type="number"
                min="1"
                value={changedFiles}
                onChange={(e) => setChangedFiles(parseInt(e.target.value) || 1)}
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  padding: '6px 8px',
                  backgroundColor: '#18181b',
                  border: '1px solid #27272a',
                  borderRadius: '6px',
                  color: '#ffffff',
                  fontSize: '12px',
                }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button
                type="submit"
                disabled={predicting || !prTitle.trim()}
                style={{
                  width: '100%',
                  padding: '7px 12px',
                  backgroundColor: '#dc2626',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '12px',
                  cursor: predicting || !prTitle.trim() ? 'not-allowed' : 'pointer',
                  opacity: predicting || !prTitle.trim() ? 0.6 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <Send size={12} />
                {predicting ? 'Estimating...' : 'Estimate Delay'}
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Prediction Output Result Box */}
      {prediction && (
        <div
          style={{
            padding: '16px',
            backgroundColor: '#18181b',
            borderRadius: '8px',
            border: '1px solid #dc2626',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
            marginTop: '12px',
          }}
        >
          <div>
            <div style={{ fontSize: '11px', color: '#ef4444', fontWeight: 600, textTransform: 'uppercase' }}>
              Estimated Time to First Review
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#ffffff', margin: '4px 0' }}>
              ~{prediction.predicted_delay_hours} Hours
            </div>
            {prediction.lower_bound_hours && prediction.upper_bound_hours && (
              <div style={{ fontSize: '12px', color: '#a1a1aa' }}>
                Uncertainty Range: {prediction.lower_bound_hours}h – {prediction.upper_bound_hours}h
              </div>
            )}
          </div>

          <div style={{ textAlign: 'right', fontSize: '12px', color: '#a1a1aa' }}>
            <div style={{ color: '#ffffff', fontWeight: 600 }}>{prediction.confidence_tier}</div>
            <div>Model: {prediction.best_model || 'HistGradientBoosting'}</div>
          </div>
        </div>
      )}

      {predictError && (
        <div style={{ color: '#ef4444', fontSize: '13px', marginTop: '8px' }}>
          {predictError}
        </div>
      )}
    </div>
  );
};
