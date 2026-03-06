/**
 * Hook: loads/registers auth on mount, exposes auth state.
 * Generates a stable device ID from expo-device if available.
 */

import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { loadAuth, registerDevice, AuthState } from '../store/auth';

const DEVICE_ID_KEY = 'device_id';

async function getOrCreateDeviceId(): Promise<string> {
  const stored = await SecureStore.getItemAsync(DEVICE_ID_KEY);
  if (stored) return stored;
  const id = `${Platform.OS}-${Math.random().toString(36).slice(2)}-${Date.now()}`;
  await SecureStore.setItemAsync(DEVICE_ID_KEY, id);
  return id;
}

export function useAuth() {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const existing = await loadAuth();
        if (existing) {
          setAuth(existing);
        } else {
          const deviceId = await getOrCreateDeviceId();
          const state = await registerDevice(deviceId);
          setAuth(state);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Auth failed');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return { auth, loading, error };
}
