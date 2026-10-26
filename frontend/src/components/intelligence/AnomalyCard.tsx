import React from 'react';
import { AnomalyResponse, AnomalyItem } from '../../types';
import { ShieldAlert, AlertTriangle, CheckCircle, Sliders } from 'lucide-react';

interface AnomalyCardProps {
  data: AnomalyResponse | null;
  loading: boolean;
  error: string | null;
  threshold: number;
  onThresholdChange: (threshold: number) => void;
}

export const AnomalyCard: React.FC<AnomalyCardProps> = ({
  data,
  loading,
  error,
  threshold,
  onThresholdChange,
}) => {
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
        <span>Running rolling MAD anomaly analysis...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div
        style={{
          padding: '24px',
          backgroundColor: '#0f172a',
          borderRadius: '12px',
          border: '1px solid #1e293b',
          color: '#f87171',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <AlertTriangle size={18} />
          <span style={{ fontWeight: 600 }}>Anomaly Detection Unavailable</span>
        </div>
        <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px' }}>
          {error || 'Unable to scan repository timeline for activity anomalies.'}
        </p>
      </div>
    );
  }

  const anomalies: AnomalyItem[] = data.anomalies || [];

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'HIGH':
        return {
          bg: 'rgba(239, 68, 68, 0.15)',
          color: '#ef4444',
          border: '1px solid rgba(239, 68, 68, 0.3)',
        };
      case 'MEDIUM':
        return {
          bg: 'rgba(245, 158, 11, 0.15)',
          color: '#f59e0b',
          border: '1px solid rgba(245, 158, 11, 0.3)',
        };
      default:
        return {
          bg: 'rgba(56, 189, 248, 0.15)',
          color: '#38bdf8',
          border: '1px solid rgba(56, 189, 248, 0.3)',
        };
    }
  };

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
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '18px',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <ShieldAlert size={20} color="#f59e0b" />
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>
              Repository Activity Anomaly Detection
            </h3>
            <span
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                backgroundColor: 'rgba(245, 158, 11, 0.15)',
                color: '#f59e0b',
                borderRadius: '9999px',
                fontWeight: 600,
              }}
            >
              Rolling MAD & Isolation Forest
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8' }}>
            Surfaces statistical surges and drops based on 14-day rolling historical medians
          </p>
        </div>

        {/* Threshold sensitivity control */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={16} color="#94a3b8" />
          <span style={{ fontSize: '12px', color: '#94a3b8' }}>Sensitivity:</span>
          <select
            value={threshold}
            onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
            style={{
              padding: '4px 8px',
              backgroundColor: '#1e293b',
              color: '#f8fafc',
              border: '1px solid #334155',
              borderRadius: '6px',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            <option value={2.5}>Sensitive (2.5σ)</option>
            <option value={3.0}>Standard (3.0σ)</option>
            <option value={4.0}>Conservative (4.0σ)</option>
          </select>
        </div>
      </div>

      {/* Stats bar */}
      <div
        style={{
          display: 'flex',
          gap: '16px',
          marginBottom: '16px',
          padding: '10px 16px',
          backgroundColor: '#1e293b',
          borderRadius: '8px',
          fontSize: '13px',
          color: '#94a3b8',
        }}
      >
        <div>
          Days Analyzed: <strong style={{ color: '#f8fafc' }}>{data.total_days_evaluated}</strong>
        </div>
        <div>
          Rolling Baseline: <strong style={{ color: '#f8fafc' }}>{data.rolling_window_days} Days</strong>
        </div>
        <div>
          Anomalies Detected:{' '}
          <strong style={{ color: anomalies.length > 0 ? '#f59e0b' : '#34d399' }}>
            {data.total_anomalies}
          </strong>
        </div>
      </div>

      {/* Anomalies List */}
      {anomalies.length === 0 ? (
        <div
          style={{
            padding: '32px 16px',
            textAlign: 'center',
            backgroundColor: 'rgba(30, 41, 59, 0.4)',
            borderRadius: '8px',
            border: '1px dashed #334155',
          }}
        >
          <CheckCircle size={28} color="#34d399" style={{ margin: '0 auto 8px auto' }} />
          <div style={{ color: '#f8fafc', fontWeight: 600, fontSize: '14px' }}>
            No Anomalies Detected
          </div>
          <p style={{ margin: '4px 0 0 0', color: '#94a3b8', fontSize: '12px' }}>
            Activity is operating within expected rolling variance thresholds.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {anomalies.map((anom, idx) => {
            const badge = getSeverityBadge(anom.severity);
            return (
              <div
                key={`${anom.date}-${anom.metric}-${idx}`}
                style={{
                  padding: '12px 16px',
                  backgroundColor: '#1e293b',
                  borderRadius: '8px',
                  border: '1px solid #334155',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <div style={{ flex: 1, minWidth: '240px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>
                      {anom.date}
                    </span>
                    <span
                      style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 600,
                        backgroundColor: badge.bg,
                        color: badge.color,
                        border: badge.border,
                      }}
                    >
                      {anom.severity}
                    </span>
                    <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                      Score: <strong>{anom.anomaly_score}</strong>
                    </span>
                  </div>
                  <div style={{ fontSize: '13px', color: '#cbd5e1' }}>{anom.explanation}</div>
                </div>

                <div style={{ textAlign: 'right', fontSize: '12px', color: '#94a3b8' }}>
                  <div>Observed: <strong style={{ color: '#f8fafc' }}>{anom.observed_value}</strong></div>
                  <div>Baseline: {anom.baseline_median}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
