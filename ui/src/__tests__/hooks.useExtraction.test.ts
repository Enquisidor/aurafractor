/**
 * TDD tests for useExtractionPoll hook.
 * The API module is mocked entirely — no network calls.
 */

import { act, renderHook } from '@testing-library/react-native';
import { useExtractionPoll } from '../hooks/useExtraction';

// Mock the API client
jest.mock('../api/client', () => ({
  extraction: {
    poll: jest.fn(),
  },
}));

import { extraction as extractionApi } from '../api/client';
const mockPoll = extractionApi.poll as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

describe('useExtractionPoll', () => {
  it('returns null data initially', () => {
    mockPoll.mockResolvedValue({ status: 'queued', extraction_id: 'e1' });
    const { result } = renderHook(() => useExtractionPoll('e1'));
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('does not poll when extractionId is null', () => {
    renderHook(() => useExtractionPoll(null));
    expect(mockPoll).not.toHaveBeenCalled();
  });

  it('polls immediately on mount', async () => {
    mockPoll.mockResolvedValue({ status: 'processing', extraction_id: 'e1' });
    const { result } = renderHook(() => useExtractionPoll('e1'));
    await act(async () => { await Promise.resolve(); });
    expect(mockPoll).toHaveBeenCalledWith('e1');
    expect(result.current.data?.status).toBe('processing');
  });

  it('stops polling on completed status', async () => {
    mockPoll.mockResolvedValue({ status: 'completed', extraction_id: 'e1', results: { sources: [] } });
    const { result } = renderHook(() => useExtractionPoll('e1'));
    await act(async () => { await Promise.resolve(); });
    expect(result.current.data?.status).toBe('completed');
    const callCount = mockPoll.mock.calls.length;

    // Advance timers — no further polls should happen
    await act(async () => { jest.advanceTimersByTime(10000); });
    expect(mockPoll.mock.calls.length).toBe(callCount);
  });

  it('stops polling on failed status', async () => {
    mockPoll.mockResolvedValue({ status: 'failed', extraction_id: 'e1' });
    const { result } = renderHook(() => useExtractionPoll('e1'));
    await act(async () => { await Promise.resolve(); });
    expect(result.current.data?.status).toBe('failed');
    const callCount = mockPoll.mock.calls.length;
    await act(async () => { jest.advanceTimersByTime(10000); });
    expect(mockPoll.mock.calls.length).toBe(callCount);
  });

  it('sets error and stops polling on API error', async () => {
    mockPoll.mockRejectedValue(new Error('network error'));
    const { result } = renderHook(() => useExtractionPoll('e1'));
    await act(async () => { await Promise.resolve(); });
    expect(result.current.error).toBe('network error');
    const callCount = mockPoll.mock.calls.length;
    await act(async () => { jest.advanceTimersByTime(10000); });
    expect(mockPoll.mock.calls.length).toBe(callCount);
  });

  it('continues polling while status is processing', async () => {
    mockPoll.mockResolvedValue({ status: 'processing', extraction_id: 'e1' });
    renderHook(() => useExtractionPoll('e1'));
    await act(async () => { await Promise.resolve(); });
    expect(mockPoll).toHaveBeenCalledTimes(1);

    mockPoll.mockResolvedValue({ status: 'processing', extraction_id: 'e1' });
    await act(async () => {
      jest.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    expect(mockPoll.mock.calls.length).toBeGreaterThan(1);
  });
});
