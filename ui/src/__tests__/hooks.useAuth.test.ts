/**
 * TDD tests for useAuth hook.
 */

import { act, renderHook } from '@testing-library/react-native';
import { useAuth } from '../hooks/useAuth';

// Mock the auth store so no real SecureStore or API calls happen
jest.mock('../store/auth', () => ({
  loadAuth: jest.fn(),
  registerDevice: jest.fn(),
  saveAuth: jest.fn(),
  clearAuth: jest.fn(),
}));

jest.mock('../hooks/useAuth', () => {
  const actual = jest.requireActual('../hooks/useAuth');
  return actual;
});

import { loadAuth, registerDevice } from '../store/auth';
const mockLoadAuth = loadAuth as jest.Mock;
const mockRegisterDevice = registerDevice as jest.Mock;

const MOCK_AUTH_STATE = {
  userId: 'user-1',
  sessionToken: 'tok',
  refreshToken: 'ref',
  subscriptionTier: 'free' as const,
  creditsRemaining: 100,
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('useAuth', () => {
  it('starts in loading state', () => {
    mockLoadAuth.mockResolvedValue(null);
    mockRegisterDevice.mockResolvedValue(MOCK_AUTH_STATE);
    const { result } = renderHook(() => useAuth());
    expect(result.current.loading).toBe(true);
    expect(result.current.auth).toBeNull();
  });

  it('loads existing auth from store without calling registerDevice', async () => {
    mockLoadAuth.mockResolvedValue(MOCK_AUTH_STATE);
    const { result } = renderHook(() => useAuth());
    await act(async () => { await Promise.resolve(); });
    expect(result.current.loading).toBe(false);
    expect(result.current.auth).toEqual(MOCK_AUTH_STATE);
    expect(mockRegisterDevice).not.toHaveBeenCalled();
  });

  it('registers a new device when no stored auth exists', async () => {
    mockLoadAuth.mockResolvedValue(null);
    mockRegisterDevice.mockResolvedValue(MOCK_AUTH_STATE);
    const { result } = renderHook(() => useAuth());
    await act(async () => { await Promise.resolve(); });
    expect(result.current.loading).toBe(false);
    expect(result.current.auth).toEqual(MOCK_AUTH_STATE);
    expect(mockRegisterDevice).toHaveBeenCalledTimes(1);
  });

  it('sets error when registration fails', async () => {
    mockLoadAuth.mockResolvedValue(null);
    mockRegisterDevice.mockRejectedValue(new Error('network error'));
    const { result } = renderHook(() => useAuth());
    await act(async () => { await Promise.resolve(); });
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('network error');
    expect(result.current.auth).toBeNull();
  });
});
