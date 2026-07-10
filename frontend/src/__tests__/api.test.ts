/**
 * Tests for src/store/api.ts — error class contracts and apiFetch core logic.
 *
 * Uses vi.stubGlobal to mock fetch without any network calls.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthError, ApiError, ValidationError } from '@/store/api';

// ── Error Classes ─────────────────────────────────────────────────────────────

describe('AuthError', () => {
  it('has name "AuthError"', () => {
    const err = new AuthError('Session expired');
    expect(err.name).toBe('AuthError');
  });

  it('inherits from Error', () => {
    expect(new AuthError('x')).toBeInstanceOf(Error);
  });

  it('carries the message', () => {
    expect(new AuthError('test msg').message).toBe('test msg');
  });
});

describe('ApiError', () => {
  it('has name "ApiError"', () => {
    expect(new ApiError(404, 'Not found').name).toBe('ApiError');
  });

  it('stores the HTTP status code', () => {
    expect(new ApiError(500, 'Server error').status).toBe(500);
  });

  it('inherits from Error', () => {
    expect(new ApiError(400, 'Bad request')).toBeInstanceOf(Error);
  });

  it('initialises data as null', () => {
    expect(new ApiError(400, 'Bad request').data).toBeNull();
  });
});

describe('ValidationError', () => {
  const issues = [{ path: 'name', message: 'Required' }];

  it('has name "ValidationError"', () => {
    expect(new ValidationError(issues).name).toBe('ValidationError');
  });

  it('stores the issue list', () => {
    expect(new ValidationError(issues).issues).toEqual(issues);
  });

  it('has a descriptive default message', () => {
    expect(new ValidationError(issues).message).toBe('Response validation failed');
  });
});

// ── apiFetch — 401 triggers auth expiry ──────────────────────────────────────

describe('apiFetch', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('throws AuthError on a 401 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(null, { status: 401 }),
    ));

    const { apiFetch } = await import('@/store/api');
    await expect(apiFetch('/auth/verify')).rejects.toBeInstanceOf(AuthError);
  });

  it('throws ApiError on a non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 }),
    ));

    const { apiFetch } = await import('@/store/api');
    await expect(apiFetch('/missing')).rejects.toBeInstanceOf(ApiError);
  });

  it('returns parsed JSON on a 200 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ token: 'abc123' }), { status: 200 }),
    ));

    const { apiFetch } = await import('@/store/api');
    const result = await apiFetch<{ token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password: 'pw' }),
    });
    expect(result.token).toBe('abc123');
  });
});
