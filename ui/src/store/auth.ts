/**
 * Auth store — session token, user info, persisted via platform storage.
 * Uses localStorage on web, expo-secure-store on native.
 */

import { storage } from '../storage/platform';
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
    storage.getItem(KEYS.sessionToken),
    storage.getItem(KEYS.refreshToken),
    storage.getItem(KEYS.userId),
    storage.getItem(KEYS.subscriptionTier),
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
    storage.setItem(KEYS.sessionToken, res.session_token),
    storage.setItem(KEYS.refreshToken, res.refresh_token),
    storage.setItem(KEYS.userId, res.user_id),
    storage.setItem(KEYS.subscriptionTier, res.subscription_tier),
  ]);
}

export async function clearAuth(): Promise<void> {
  await Promise.all(Object.values(KEYS).map((k) => storage.removeItem(k)));
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
  await storage.setItem(KEYS.sessionToken, res.session_token);
  return res.session_token;
}
