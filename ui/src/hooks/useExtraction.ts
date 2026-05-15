/**
 * Hook: polls extraction status every 5 s until completed or failed.
 * After each successful poll, the result is upserted into the Redux
 * extractions cache. The calling screen (which is wrapped in a Redux
 * Provider) handles the dispatch via the returned `data` value — each
 * new non-null data value should be dispatched as upsertExtraction.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { extraction as extractionApi, ExtractionResponse } from '../api/client';

const POLL_INTERVAL_MS = 5000;
const TERMINAL_STATUSES = new Set(['completed', 'failed']);

export function useExtractionPoll(extractionId: string | null) {
  const [data, setData] = useState<ExtractionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!extractionId) return;

    const poll = async () => {
      try {
        const res = await extractionApi.poll(extractionId);
        setData(res);
        if (TERMINAL_STATUSES.has(res.status)) stop();
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Poll failed');
        stop();
      }
    };

    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return stop;
  }, [extractionId, stop]);

  return { data, error };
}
