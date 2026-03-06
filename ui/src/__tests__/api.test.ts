/**
 * Unit tests for the API client utilities.
 * Network calls are mocked — no real backend required.
 */

import { ApiError, BASE_URL } from '../api/client';

describe('ApiError', () => {
  it('carries status code', () => {
    const err = new ApiError('Not found', 404);
    expect(err.message).toBe('Not found');
    expect(err.status).toBe(404);
    expect(err.name).toBe('ApiError');
  });

  it('is instanceof Error', () => {
    expect(new ApiError('x', 500)).toBeInstanceOf(Error);
  });
});

describe('BASE_URL', () => {
  it('exports a non-empty string', () => {
    expect(typeof BASE_URL).toBe('string');
    expect(BASE_URL.length).toBeGreaterThan(0);
  });
});
