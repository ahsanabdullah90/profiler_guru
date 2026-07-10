/**
 * Tests for src/store/authStore.ts
 *
 * Covers: setAuthenticated localStorage persistence, login happy/error paths,
 * and verifyToken early exit when no saved token exists.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

async function freshAuthStore() {
  vi.resetModules();
  const { useAuthStore } = await import('@/store/authStore');
  return useAuthStore;
}

describe('authStore — setAuthenticated', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('persists the token in localStorage when authenticated', async () => {
    const useAuthStore = await freshAuthStore();
    useAuthStore.getState().setAuthenticated(true, 'my-token');
    expect(localStorage.getItem('auth_token')).toBe('my-token');
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().token).toBe('my-token');
  });

  it('removes the token from localStorage on logout', async () => {
    const useAuthStore = await freshAuthStore();
    useAuthStore.getState().setAuthenticated(true, 'my-token');
    useAuthStore.getState().setAuthenticated(false, null);
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().token).toBeNull();
  });
});

describe('authStore — login', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('stores the token and returns true on successful login', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ token: 'jwt-from-server' }), { status: 200 }),
    ));

    const useAuthStore = await freshAuthStore();
    const result = await useAuthStore.getState().login('correct-password');

    expect(result).toBe(true);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().token).toBe('jwt-from-server');
  });

  it('throws and does not authenticate on a failed login', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Invalid password' }), { status: 401 }),
    ));

    const useAuthStore = await freshAuthStore();
    await expect(useAuthStore.getState().login('wrong-password')).rejects.toThrow();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});

describe('authStore — verifyToken', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('sets isAuthenticated to false when no saved token exists', async () => {
    const useAuthStore = await freshAuthStore();
    await useAuthStore.getState().verifyToken();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
