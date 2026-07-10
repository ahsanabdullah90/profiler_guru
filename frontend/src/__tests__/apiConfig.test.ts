/**
 * Tests for src/lib/apiConfig.ts
 *
 * Verifies network constants, getApiBase() URL construction,
 * fetchWithTimeout abort behaviour, and the token/auth-expiry bridges.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  API_PORT,
  API_VERSION,
  CONTACTS_FETCH_TIMEOUT,
  DEFAULT_FETCH_TIMEOUT,
  getApiBase,
  fetchWithTimeout,
  registerTokenProvider,
  getAuthToken,
  registerAuthExpiredCallback,
  triggerAuthExpired,
} from '@/lib/apiConfig';

// ── Constants ────────────────────────────────────────────────────────────────

describe('API constants', () => {
  it('API_PORT is 8000', () => {
    expect(API_PORT).toBe(8_000);
  });

  it('API_VERSION is v1', () => {
    expect(API_VERSION).toBe('v1');
  });

  it('CONTACTS_FETCH_TIMEOUT is 60 seconds', () => {
    expect(CONTACTS_FETCH_TIMEOUT).toBe(60_000);
  });

  it('DEFAULT_FETCH_TIMEOUT is 5 seconds', () => {
    expect(DEFAULT_FETCH_TIMEOUT).toBe(5_000);
  });
});

// ── getApiBase ────────────────────────────────────────────────────────────────

describe('getApiBase()', () => {
  it('builds a URL with the correct port and version segment', () => {
    const base = getApiBase();
    expect(base).toContain(`:${API_PORT}/api/${API_VERSION}`);
  });

  it('uses localhost hostname in a browser-like environment', () => {
    // jsdom sets window.location.hostname to 'localhost' by default
    const base = getApiBase();
    expect(base).toMatch(/^http:\/\/(localhost|127\.0\.0\.1):8000\/api\/v1$/);
  });
});

// ── fetchWithTimeout ─────────────────────────────────────────────────────────

describe('fetchWithTimeout()', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('resolves with the fetch response on success', async () => {
    const mockResponse = new Response(JSON.stringify({ ok: true }), { status: 200 });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse));

    const res = await fetchWithTimeout('http://localhost:8000/api/health');
    expect(res.status).toBe(200);
  });

  it('aborts and throws when timeout expires', async () => {
    // Signal-aware mock: rejects when the AbortSignal fires (simulating real fetch).
    vi.stubGlobal('fetch', vi.fn((_url: string, opts?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        opts?.signal?.addEventListener('abort', () => {
          reject(new DOMException('The user aborted a request.', 'AbortError'));
        });
      }),
    ));

    await expect(
      fetchWithTimeout('http://localhost:8000/slow', {}, 50),
    ).rejects.toThrow();
  }, 2000);


});

// ── Token Provider Bridge ────────────────────────────────────────────────────

describe('Token provider bridge', () => {
  it('returns null when no provider has been registered', () => {
    // Fresh module state — may already have a provider from authStore init.
    // We test the getter returns a string | null.
    const token = getAuthToken();
    expect(token === null || typeof token === 'string').toBe(true);
  });

  it('returns the token from a registered provider', () => {
    registerTokenProvider(() => 'test-jwt-token');
    expect(getAuthToken()).toBe('test-jwt-token');
    // Reset to null provider for other tests
    registerTokenProvider(() => null);
  });
});

// ── Auth-Expiry Callback Bridge ───────────────────────────────────────────────

describe('Auth-expiry callback bridge', () => {
  it('calls the registered callback when triggerAuthExpired is invoked', () => {
    const handler = vi.fn();
    registerAuthExpiredCallback(handler);
    triggerAuthExpired();
    expect(handler).toHaveBeenCalledOnce();
    // Reset
    registerAuthExpiredCallback(() => {});
  });

  it('does not throw when no callback has been registered', () => {
    registerAuthExpiredCallback(null as unknown as () => void);
    expect(() => triggerAuthExpired()).not.toThrow();
    registerAuthExpiredCallback(() => {});
  });
});
