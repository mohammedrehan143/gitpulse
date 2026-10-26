import { useEffect, useState, useCallback, useRef } from 'react';
import { sendKeepAlivePulse } from '../services/api';
import { KeepAliveResponse } from '../types';

interface UseKeepAliveReturn {
  lastPulse: KeepAliveResponse | null;
  lastPulseAt: Date | null;
  pulseCount: number;
  isPulsing: boolean;
  error: string | null;
  triggerPulse: (sync?: boolean) => Promise<void>;
}

const FIVE_MINUTES_MS = 5 * 60 * 1000;

export const useKeepAlive = (intervalMs: number = FIVE_MINUTES_MS): UseKeepAliveReturn => {
  const [lastPulse, setLastPulse] = useState<KeepAliveResponse | null>(null);
  const [lastPulseAt, setLastPulseAt] = useState<Date | null>(null);
  const [pulseCount, setPulseCount] = useState<number>(0);
  const [isPulsing, setIsPulsing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const isMountedRef = useRef(true);

  const triggerPulse = useCallback(async (sync: boolean = false) => {
    setIsPulsing(true);
    setError(null);
    try {
      const res = await sendKeepAlivePulse(sync);
      if (isMountedRef.current) {
        setLastPulse(res);
        setLastPulseAt(new Date());
        setPulseCount((c) => c + 1);
      }
    } catch (err: unknown) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : 'Keep-alive pulse failed');
      }
    } finally {
      if (isMountedRef.current) {
        setIsPulsing(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;

    // Send initial warm-up pulse on mount
    triggerPulse(false);

    // Schedule recursive 5-minute keep-alive interval
    const timerId = setInterval(() => {
      triggerPulse(false);
    }, intervalMs);

    return () => {
      isMountedRef.current = false;
      clearInterval(timerId);
    };
  }, [triggerPulse, intervalMs]);

  return {
    lastPulse,
    lastPulseAt,
    pulseCount,
    isPulsing,
    error,
    triggerPulse,
  };
};
