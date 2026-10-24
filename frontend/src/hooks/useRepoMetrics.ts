import { useState, useEffect } from 'react';
import { VelocityResponse } from '../types';
import { fetchRepositoryVelocity } from '../services/api';

export function useRepoMetrics(owner: string, repo: string, timeframe = '30d') {
  const [data, setData] = useState<VelocityResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchRepositoryVelocity(owner, repo, timeframe)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load repository velocity data');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [owner, repo, timeframe]);

  return { data, loading, error };
}
