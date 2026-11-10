import React, { useState } from 'react';
import { RefreshCw, Database, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';
import { SyncCheckpointItem } from '../types';
import { syncRepository, reconcileRepository } from '../services/api';

interface CheckpointsCardProps {
  owner: string;
  repo: string;
  checkpoints: SyncCheckpointItem[];
  lastSyncedAt?: string | null;
  onRefreshStats: () => void;
}

export const CheckpointsCard: React.FC<CheckpointsCardProps> = ({
  owner,
  repo,
  checkpoints,
  lastSyncedAt,
  onRefreshStats,
}) => {
  const [syncing, setSyncing] = useState(false);
  const [reconciling, setReconciling] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const handleSync = async () => {
    setSyncing(true);
    setActionMessage(null);
    try {
      const res = await syncRepository(owner, repo, true);
      setActionMessage(`Incremental sync completed: ${res.records_processed} records synced (${res.duration_seconds.toFixed(1)}s)`);
      onRefreshStats();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Sync failed';
      setActionMessage(`Sync error: ${msg}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleReconcile = async () => {
    setReconciling(true);
    setActionMessage(null);
    try {
      const res = await reconcileRepository(owner, repo);
      setActionMessage(`Data reconciliation complete! Added ${res.commits.newly_added} commits, ${res.pull_requests.newly_added} PRs, ${res.issues.newly_added} issues.`);
      onRefreshStats();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Reconciliation failed';
      setActionMessage(`Reconciliation error: ${msg}`);
    } finally {
      setReconciling(false);
    }
  };

  return (
    <div
      style={{
        backgroundColor: '#121212',
        border: '1px solid #27272a',
        borderRadius: '12px',
        padding: '1.25rem',
        marginBottom: '1.5rem',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={18} color="#dc2626" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
            Data Pipeline & Synchronization Checkpoints
          </h3>
          {lastSyncedAt && (
            <span style={{ fontSize: '11px', color: '#71717a' }}>
              (Last synced: {new Date(lastSyncedAt).toLocaleTimeString()})
            </span>
          )}
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleSync}
            disabled={syncing || reconciling}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: '6px',
              border: '1px solid #3f3f46',
              backgroundColor: '#18181b',
              color: '#ffffff',
              cursor: syncing ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <RefreshCw size={13} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Syncing...' : 'Sync Pipeline'}
          </button>

          <button
            onClick={handleReconcile}
            disabled={syncing || reconciling}
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: '6px',
              border: '1px solid #dc2626',
              backgroundColor: '#dc2626',
              color: '#ffffff',
              cursor: reconciling ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <ShieldCheck size={13} className={reconciling ? 'animate-spin' : ''} />
            {reconciling ? 'Reconciling...' : 'Reconcile Data'}
          </button>
        </div>
      </div>

      {actionMessage && (
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: actionMessage.includes('error') ? 'rgba(239, 68, 68, 0.15)' : 'rgba(34, 197, 94, 0.15)',
            border: `1px solid ${actionMessage.includes('error') ? 'rgba(239, 68, 68, 0.3)' : 'rgba(34, 197, 94, 0.3)'}`,
            borderRadius: '6px',
            color: actionMessage.includes('error') ? '#fca5a5' : '#86efac',
            fontSize: '12px',
            marginBottom: '1rem',
          }}
        >
          {actionMessage}
        </div>
      )}

      {/* Checkpoints Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: '8px',
        }}
      >
        {checkpoints.length === 0 ? (
          <div style={{ color: '#71717a', fontSize: '12px', padding: '8px 0' }}>
            No checkpoints recorded yet. Run a pipeline sync to create incremental markers.
          </div>
        ) : (
          checkpoints.map((cp) => (
            <div
              key={cp.resource_type}
              style={{
                backgroundColor: '#18181b',
                border: '1px solid #27272a',
                borderRadius: '6px',
                padding: '8px 10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', textTransform: 'capitalize' }}>
                  {cp.resource_type}
                </div>
                <div style={{ fontSize: '10px', color: '#71717a' }}>
                  {cp.records_synced} synced
                </div>
              </div>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '2px',
                  fontSize: '10px',
                  fontWeight: 700,
                  color: cp.status === 'COMPLETED' ? '#4ade80' : '#f87171',
                }}
              >
                {cp.status === 'COMPLETED' ? <CheckCircle2 size={11} /> : <AlertTriangle size={11} />}
                {cp.status}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
