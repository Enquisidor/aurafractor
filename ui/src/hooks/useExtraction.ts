/**
 * Hook: polls extraction status every 5 s until completed or failed.
 * After each successful poll, the result is upserted into the Redux
 * extractions cache. The calling screen (which is wrapped in a Redux
 * Provider) handles the dispatch via the returned `data` value — each
 * new non-null data value should be dispatched as upsertExtraction.
 *
 * Hung-state detection:
 *   isHung is set to true when status === 'processing' and the elapsed
 *   time since processing began exceeds HUNG_THRESHOLD_MS (10 minutes).
 *   Elapsed time is derived from the response's started_at field when
 *   available. When started_at is null or absent, elapsed time is measured
 *   from when the hook first observed status === 'processing' (tracked via
 *   processingStartedAtRef). Polling continues even when isHung is true —
 *   the backend may eventually complete.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { extraction as extractionApi, ExtractionResponse } from '../api/client';

const POLL_INTERVAL_MS = 5000;
const TERMINAL_STATUSES = new Set(['completed', 'failed']);
/** 10 minutes in milliseconds. See DEC-013 for threshold rationale. */
export const HUNG_THRESHOLD_MS = 10 * 60 * 1000;

export function useExtractionPoll(extractionId: string | null) {
  const [data, setData] = useState<ExtractionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isHung, setIsHung] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  /**
   * Timestamp (ms) of when we first observed status === 'processing',
   * used as a fallback when started_at is null.
   */
  const processingStartedAtRef = useRef<number | null>(null);

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

        if (TERMINAL_STATUSES.has(res.status)) {
          // Clear hung state on terminal resolution and reset fallback timer.
          processingStartedAtRef.current = null;
          setIsHung(false);
          stop();
          return;
        }

        if (res.status === 'processing') {
          // Determine the effective processing start time.
          let processingStartMs: number;

          if (res.started_at) {
            processingStartMs = new Date(res.started_at).getTime();
          } else {
            // Fall back to the local timestamp of first processing observation.
            if (processingStartedAtRef.current === null) {
              processingStartedAtRef.current = Date.now();
            }
            processingStartMs = processingStartedAtRef.current;
          }

          const elapsed = Date.now() - processingStartMs;
          setIsHung(elapsed >= HUNG_THRESHOLD_MS);
        } else {
          // Status changed away from processing (e.g. queued again) — reset.
          processingStartedAtRef.current = null;
          setIsHung(false);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Poll failed');
        stop();
      }
    };

    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return stop;
  }, [extractionId, stop]);

  return { data, error, isHung };
}
