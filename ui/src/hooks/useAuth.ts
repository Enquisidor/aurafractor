/**
 * Hook: loads/registers auth on mount, exposes auth state.
 * Generates a stable device ID stored via platform storage.
 * Exposes a `retry` function so callers can re-attempt auth after an error.
 * Exposes `isNewUser` (true only after a successful first-time registration)
 * so the root layout can trigger the first-launch confirmation UI.
 */

import { useCallback, useEffect, useState } from 'react';
import { Platform } from 'react-native';
import { storage } from '../storage/platform';
import { loadAuth, registerDevice, AuthState } from '../store/auth';

const DEVICE_ID_KEY = 'device_id';

async function getOrCreateDeviceId(): Promise<string> {
  const stored = await storage.getItem(DEVICE_ID_KEY);
  if (stored) return stored;
  const id = `${Platform.OS}-${Math.random().toString(36).slice(2)}-${Date.now()}`;
  await storage.setItem(DEVICE_ID_KEY, id);
  return id;
}

export function useAuth() {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isNewUser, setIsNewUser] = useState(false);
  // Incrementing this counter re-triggers the auth effect (retry).
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const existing = await loadAuth();
        if (cancelled) return;
        if (existing) {
          setAuth(existing);
          // Loading from storage means a returning user — isNewUser stays false
          setIsNewUser(false);
        } else {
          const deviceId = await getOrCreateDeviceId();
          const state = await registerDevice(deviceId);
          if (!cancelled) {
            setAuth(state);
            setIsNewUser(state.isNewUser ?? false);
          }
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Auth failed');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [attempt]);

  const retry = useCallback(() => {
    setAttempt((n) => n + 1);
  }, []);

  return { auth, loading, error, retry, isNewUser };
}
