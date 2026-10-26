import React, { useState } from 'react';
import { ActivityForecastResponse } from '../../types';
import { TrendingUp, AlertCircle, Calendar, Sparkles } from 'lucide-react';

interface ForecastingCardProps {
  data: ActivityForecastResponse | null;
  loading: boolean;
  error: string | null;
  horizon: number;
  onHorizonChange: (horizon: number) => void;
}

export const ForecastingCard: React.FC<ForecastingCardProps> = ({
  data,
  loading,
  error,
  horizon,
  onHorizonChange,
}) => {
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);

  if (loading) {
    return (
      <div
        className="card-loading"
        style={{
          padding: '24px',
          backgroundColor: '#0f172a',
          borderRadius: '12px',
          border: '1px solid #1e293b',
          color: '#94a3b8',
          minHeight: '320px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span>Loading developer activity forecasting...</span>
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
          <AlertCircle size={18} />
          <span style={{ fontWeight: 600 }}>Forecasting Unavailable</span>
        </div>
        <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px' }}>
          {error || 'Unable to generate future activity predictions at this time.'}
        </p>
      </div>
    );
  }

  if (data.status === 'INSUFFICIENT_HISTORY') {
    return (
      <div
        style={{
          padding: '24px',
          backgroundColor: '#0f172a',
          borderRadius: '12px',
          border: '1px solid #1e293b',
          color: '#f59e0b',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <Calendar size={18} />
          <span style={{ fontWeight: 600 }}>Insufficient Historical Continuity</span>
        </div>
        <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px' }}>
          {data.message || 'At least 14 days of activity history are required to train autoregressive forecasting models.'}
        </p>
      </div>
    );
  }

  const forecast = data.forecast || [];
  const evalMetrics = data.evaluation;
  const maxVal = Math.max(...forecast.map((f) => f.upper_bound), 10);

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
            <TrendingUp size={20} color="#38bdf8" />
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>
              Developer Activity Forecasting
            </h3>
            <span
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                backgroundColor: 'rgba(56, 189, 248, 0.15)',
                color: '#38bdf8',
                borderRadius: '9999px',
                fontWeight: 600,
              }}
            >
              ML Autoregressive
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8' }}>
            Projected commit & activity trajectory with 95% uncertainty intervals
          </p>
        </div>

        {/* Horizon selector buttons */}
        <div style={{ display: 'flex', gap: '6px', backgroundColor: '#1e293b', padding: '4px', borderRadius: '8px' }}>
          <button
            onClick={() => onHorizonChange(7)}
            style={{
              padding: '4px 12px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: horizon === 7 ? '#38bdf8' : 'transparent',
              color: horizon === 7 ? '#0f172a' : '#94a3b8',
              transition: 'all 0.15s ease',
            }}
          >
            Next 7 Days
          </button>
          <button
            onClick={() => onHorizonChange(14)}
            style={{
              padding: '4px 12px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: horizon === 14 ? '#38bdf8' : 'transparent',
              color: horizon === 14 ? '#0f172a' : '#94a3b8',
              transition: 'all 0.15s ease',
            }}
          >
            Next 14 Days
          </button>
        </div>
      </div>

      {/* Model Performance Evaluation Strip */}
      {evalMetrics && (
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8' }}>
            <Sparkles size={16} />
            <span style={{ fontWeight: 600 }}>Validation Backtest:</span>
          </div>
          <div style={{ color: '#94a3b8' }}>
            Seasonal Baseline MAE: <strong style={{ color: '#e2e8f0' }}>{evalMetrics.seasonal_naive_mae}</strong>
          </div>
          <div style={{ color: '#94a3b8' }}>
            ML Model MAE: <strong style={{ color: '#34d399' }}>{evalMetrics.ml_model_mae}</strong>
          </div>
          {evalMetrics.mae_improvement_pct > 0 && (
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
              +{evalMetrics.mae_improvement_pct}% vs Baseline
            </span>
          )}
        </div>
      )}

      {/* Visual Forecast Timeline Bar / Area Display */}
      <div style={{ marginTop: '16px' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${forecast.length}, 1fr)`,
            gap: '8px',
            alignItems: 'flex-end',
            height: '180px',
            paddingBottom: '8px',
            borderBottom: '1px solid #334155',
          }}
        >
          {forecast.map((pt) => {
            const heightPct = Math.round((pt.forecast / maxVal) * 100);
            const lowerPct = Math.round((pt.lower_bound / maxVal) * 100);
            const upperPct = Math.round((pt.upper_bound / maxVal) * 100);
            const isHovered = hoveredDate === pt.date;

            return (
              <div
                key={pt.date}
                onMouseEnter={() => setHoveredDate(pt.date)}
                onMouseLeave={() => setHoveredDate(null)}
                style={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'flex-end',
                  alignItems: 'center',
                  cursor: 'pointer',
                  position: 'relative',
                }}
              >
                {/* Uncertainty Interval Indicator Line */}
                <div
                  style={{
                    position: 'absolute',
                    bottom: `${lowerPct}%`,
                    height: `${Math.max(upperPct - lowerPct, 4)}%`,
                    width: '6px',
                    backgroundColor: 'rgba(56, 189, 248, 0.25)',
                    borderRadius: '4px',
                  }}
                />

                {/* Point Value Bar */}
                <div
                  style={{
                    width: '100%',
                    maxWidth: '32px',
                    height: `${Math.max(heightPct, 6)}%`,
                    backgroundColor: isHovered ? '#38bdf8' : pt.is_weekend ? '#64748b' : '#0284c7',
                    borderRadius: '4px 4px 0 0',
                    transition: 'all 0.15s ease',
                    zIndex: 2,
                  }}
                />

                {/* Tooltip on Hover */}
                {isHovered && (
                  <div
                    style={{
                      position: 'absolute',
                      bottom: '105%',
                      backgroundColor: '#020617',
                      border: '1px solid #38bdf8',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      whiteSpace: 'nowrap',
                      zIndex: 10,
                      boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                    }}
                  >
                    <div style={{ color: '#f8fafc', fontWeight: 600 }}>{pt.date}</div>
                    <div style={{ color: '#38bdf8' }}>Forecast: {pt.forecast} commits</div>
                    <div style={{ color: '#94a3b8' }}>Range: {pt.lower_bound} – {pt.upper_bound}</div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Date labels */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${forecast.length}, 1fr)`,
            gap: '8px',
            marginTop: '8px',
          }}
        >
          {forecast.map((pt) => {
            const shortDate = pt.date.slice(5); // MM-DD
            return (
              <div
                key={pt.date}
                style={{
                  textAlign: 'center',
                  fontSize: '11px',
                  color: pt.is_weekend ? '#64748b' : '#94a3b8',
                }}
              >
                {shortDate}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
