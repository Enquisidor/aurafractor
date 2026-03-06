/**
 * Tests for auth store utilities.
 * expo-secure-store is mocked via __mocks__/expo-secure-store.ts.
 */

import { clearAuth, loadAuth, saveAuth } from '../store/auth';

const MOCK_AUTH_RESPONSE = {
  user_id: 'user-123',
  session_token: 'sess-abc',
  refresh_token: 'ref-xyz',
  expires_in: 86400,
  subscription_tier: 'free' as const,
  credits_remaining: 100,
  is_new_user: true,
  timestamp: new Date().toISOString(),
};

describe('auth store', () => {
  beforeEach(async () => {
    await clearAuth();
  });

  it('loadAuth returns null when no tokens stored', async () => {
    expect(await loadAuth()).toBeNull();
  });

  it('saveAuth then loadAuth returns correct state', async () => {
    await saveAuth(MOCK_AUTH_RESPONSE);
    const state = await loadAuth();
    expect(state).not.toBeNull();
    expect(state!.userId).toBe('user-123');
    expect(state!.sessionToken).toBe('sess-abc');
    expect(state!.refreshToken).toBe('ref-xyz');
    expect(state!.subscriptionTier).toBe('free');
  });

  it('clearAuth removes stored tokens', async () => {
    await saveAuth(MOCK_AUTH_RESPONSE);
    await clearAuth();
    expect(await loadAuth()).toBeNull();
  });
});
