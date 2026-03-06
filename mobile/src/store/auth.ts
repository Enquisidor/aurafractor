/**
 * Auth store — session token, user info, persisted via SecureStore.
 * Minimal global state; no external state library needed.
 */

import * as SecureStore from 'expo-secure-store';
import { auth as authApi, AuthResponse } from '../api/client';

const KEYS = {
  sessionToken: 'session_token',
  refreshToken: 'refresh_token',
  userId: 'user_id',
  subscriptionTier: 'subscription_tier',
} as const;

export interface AuthState {
  userId: string;
  sessionToken: string;
  refreshToken: string;
  subscriptionTier: 'free' | 'pro' | 'studio';
  creditsRemaining: number;
}

export async function loadAuth(): Promise<AuthState | null> {
  const [sessionToken, refreshToken, userId, subscriptionTier] = await Promise.all([
    SecureStore.getItemAsync(KEYS.sessionToken),
    SecureStore.getItemAsync(KEYS.refreshToken),
    SecureStore.getItemAsync(KEYS.userId),
    SecureStore.getItemAsync(KEYS.subscriptionTier),
  ]);
  if (!sessionToken || !refreshToken || !userId) return null;
  return {
    userId,
    sessionToken,
    refreshToken,
    subscriptionTier: (subscriptionTier as AuthState['subscriptionTier']) ?? 'free',
    creditsRemaining: 0,
  };
}

export async function saveAuth(res: AuthResponse): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(KEYS.sessionToken, res.session_token),
    SecureStore.setItemAsync(KEYS.refreshToken, res.refresh_token),
    SecureStore.setItemAsync(KEYS.userId, res.user_id),
    SecureStore.setItemAsync(KEYS.subscriptionTier, res.subscription_tier),
  ]);
}

export async function clearAuth(): Promise<void> {
  await Promise.all(Object.values(KEYS).map((k) => SecureStore.deleteItemAsync(k)));
}

export async function registerDevice(deviceId: string): Promise<AuthState> {
  const res = await authApi.register(deviceId, '1.0.0');
  await saveAuth(res);
  return {
    userId: res.user_id,
    sessionToken: res.session_token,
    refreshToken: res.refresh_token,
    subscriptionTier: res.subscription_tier,
    creditsRemaining: res.credits_remaining,
  };
}

export async function refreshSession(refreshToken: string): Promise<string> {
  const res = await authApi.refresh(refreshToken);
  await SecureStore.setItemAsync(KEYS.sessionToken, res.session_token);
  return res.session_token;
}
