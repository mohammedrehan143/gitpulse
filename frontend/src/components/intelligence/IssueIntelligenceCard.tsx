import React, { useState } from 'react';
import { IssueResolutionInsights, IssuePredictResponse } from '../../types';
import { Clock, Cpu, Send } from 'lucide-react';

interface IssueIntelligenceCardProps {
  insights: IssueResolutionInsights | null;
  loading: boolean;
  onPredict: (title: string, labels: string[]) => Promise<IssuePredictResponse>;
}

export const IssueIntelligenceCard: React.FC<IssueIntelligenceCardProps> = ({
  insights,
  loading,
  onPredict,
}) => {
  const [issueTitle, setIssueTitle] = useState('');
  const [selectedLabels, setSelectedLabels] = useState<string[]>(['bug']);
  const [prediction, setPrediction] = useState<IssuePredictResponse | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [predictError, setPredictError] = useState<string | null>(null);

  const availableLabels = ['bug', 'enhancement', 'documentation', 'critical', 'backend', 'ui', 'performance'];

  const toggleLabel = (label: string) => {
    setSelectedLabels((prev) =>
      prev.includes(label) ? prev.filter((l) => l !== label) : [...prev, label]
    );
  };

  const handlePredictSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueTitle.trim()) return;
    setPredicting(true);
    setPredictError(null);
    try {
      const res = await onPredict(issueTitle, selectedLabels);
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
          backgroundColor: '#0f172a',
          borderRadius: '12px',
          border: '1px solid #1e293b',
          color: '#94a3b8',
          minHeight: '280px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span>Loading issue turnaround intelligence...</span>
      </div>
    );
  }

  const baseline = insights?.baseline_metrics;
  const bestModel = insights?.best_model || 'HistGradientBoosting';
  const models = insights?.candidate_models;

  return (
    <div
      style={{
        padding: '24px',
        backgroundColor: '#0f172a',
        borderRadius: '12px',
        border: '1px solid #1e293b',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <Clock size={20} color="#a855f7" />
          <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>
            Issue Resolution Duration Intelligence
          </h3>
          <span
            style={{
              fontSize: '11px',
              padding: '2px 8px',
              backgroundColor: 'rgba(168, 85, 247, 0.15)',
              color: '#c084fc',
              borderRadius: '9999px',
              fontWeight: 600,
            }}
          >
            Chronological Validation
          </span>
        </div>
        <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8' }}>
          ML estimation of resolution hours based on label tags, description complexity, and historical backlog
        </p>
      </div>

      {/* Model Benchmark Comparison Strip */}
      {baseline && (
        <div
          style={{
            display: 'flex',
            gap: '12px',
            marginBottom: '20px',
            padding: '12px 16px',
            backgroundColor: '#1e293b',
            borderRadius: '8px',
            fontSize: '13px',
            flexWrap: 'wrap',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#c084fc' }}>
            <Cpu size={16} />
            <span style={{ fontWeight: 600 }}>Trained Ensemble ({bestModel}):</span>
          </div>
          <div style={{ color: '#94a3b8' }}>
            Historical Median: <strong style={{ color: '#f8fafc' }}>{baseline.median_hours}h</strong>
          </div>
          <div style={{ color: '#94a3b8' }}>
            Baseline MAE: <strong style={{ color: '#f8fafc' }}>{baseline.mae_hours}h</strong>
          </div>
          {models && models[bestModel] && (
            <div style={{ color: '#94a3b8' }}>
              Ensemble MAE: <strong style={{ color: '#34d399' }}>{models[bestModel].mae_hours}h</strong>
            </div>
          )}
          {insights?.improvement_over_baseline_pct ? (
            <span
              style={{
                marginLeft: 'auto',
                padding: '2px 8px',
                backgroundColor: 'rgba(52, 211, 153, 0.15)',
                color: '#34d399',
                borderRadius: '6px',
                fontWeight: 600,
                fontSize: '12px',
              }}
            >
              +{insights.improvement_over_baseline_pct}% Accuracy Gain
            </span>
          ) : null}
        </div>
      )}

      {/* Interactive Estimator Form */}
      <form onSubmit={handlePredictSubmit} style={{ marginTop: '16px' }}>
        <div style={{ marginBottom: '12px' }}>
          <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px', fontWeight: 600 }}>
            Simulate Candidate Issue:
          </label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              placeholder="e.g., Fix database connection pool timeout on burst requests"
              value={issueTitle}
              onChange={(e) => setIssueTitle(e.target.value)}
              style={{
                flex: 1,
                padding: '8px 12px',
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '6px',
                color: '#f8fafc',
                fontSize: '13px',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={predicting || !issueTitle.trim()}
              style={{
                padding: '8px 16px',
                backgroundColor: '#a855f7',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 600,
                fontSize: '13px',
                cursor: predicting || !issueTitle.trim() ? 'not-allowed' : 'pointer',
                opacity: predicting || !issueTitle.trim() ? 0.6 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Send size={14} />
              {predicting ? 'Estimating...' : 'Estimate Duration'}
            </button>
          </div>
        </div>

        {/* Labels chips */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '16px' }}>
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>Labels:</span>
          {availableLabels.map((lbl) => {
            const isSelected = selectedLabels.includes(lbl);
            return (
              <button
                type="button"
                key={lbl}
                onClick={() => toggleLabel(lbl)}
                style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  border: isSelected ? '1px solid #c084fc' : '1px solid #334155',
                  backgroundColor: isSelected ? 'rgba(168, 85, 247, 0.2)' : '#1e293b',
                  color: isSelected ? '#c084fc' : '#94a3b8',
                  cursor: 'pointer',
                }}
              >
                {lbl}
              </button>
            );
          })}
        </div>
      </form>

      {/* Prediction Output Result Box */}
      {prediction && (
        <div
          style={{
            padding: '16px',
            backgroundColor: 'rgba(168, 85, 247, 0.1)',
            borderRadius: '8px',
            border: '1px solid rgba(168, 85, 247, 0.3)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div>
            <div style={{ fontSize: '11px', color: '#c084fc', fontWeight: 600, textTransform: 'uppercase' }}>
              Projected Time to Resolution
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc', margin: '4px 0' }}>
              ~{prediction.predicted_duration_hours} Hours
              <span style={{ fontSize: '13px', fontWeight: 400, color: '#94a3b8', marginLeft: '8px' }}>
                ({(prediction.predicted_duration_hours / 24).toFixed(1)} Days)
              </span>
            </div>
            {prediction.lower_bound_hours && prediction.upper_bound_hours && (
              <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                Uncertainty Range: {prediction.lower_bound_hours}h – {prediction.upper_bound_hours}h
              </div>
            )}
          </div>

          <div style={{ textAlign: 'right', fontSize: '12px', color: '#94a3b8' }}>
            <div style={{ color: '#c084fc', fontWeight: 600 }}>{prediction.confidence_tier}</div>
            <div>Model: {prediction.best_model || 'HistGradientBoosting'}</div>
          </div>
        </div>
      )}

      {predictError && (
        <div style={{ color: '#f87171', fontSize: '13px', marginTop: '8px' }}>
          {predictError}
        </div>
      )}
    </div>
  );
};
