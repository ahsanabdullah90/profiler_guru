import { create } from 'zustand';
import { apiFetch, fetchWithTimeout, ApiError } from './api';
import { useStatusStore } from './statusStore';

const RAW_API_BASE = (() => {
  const host = typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1';
  return `http://${host}:8000`;
})();

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  isBackendOffline: boolean;

  setAuthenticated: (auth: boolean, token: string | null) => void;
  login: (password: string) => Promise<boolean>;
  verifyToken: () => Promise<void>;
  checkBackendHealth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  isAuthenticated: false,
  token: null,
  isBackendOffline: false,

  setAuthenticated: (auth, token) => {
    if (typeof window !== 'undefined') {
      if (auth && token) {
        localStorage.setItem('auth_token', token);
      } else {
        localStorage.removeItem('auth_token');
      }
    }
    set({ isAuthenticated: auth, token });
  },

  login: async (password) => {
    try {
      const data = await apiFetch<{ token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
      });
      get().setAuthenticated(true, data.token);
      return true;
    } catch (err) {
      const e = err as Error;
      useStatusStore.getState().pushError(`Login failed: ${e.message}`, 'error');
      throw e;
    }
  },

  verifyToken: async () => {
    const win = window as unknown as { _global_error_registered?: boolean };
    if (typeof window !== 'undefined' && !win._global_error_registered) {
      win._global_error_registered = true;
      window.addEventListener('error', (event) => {
        useStatusStore.getState().pushError(`Unhandled error: ${event.message}`, 'error');
      });
      window.addEventListener('unhandledrejection', (event) => {
        const reason = event.reason;
        const msg = reason instanceof Error ? reason.message : String(reason);
        useStatusStore.getState().pushError(`Promise rejection: ${msg}`, 'error');
      });
    }

    const savedToken = localStorage.getItem('auth_token');
    if (!savedToken) {
      set({ isAuthenticated: false, token: null });
      return;
    }
    set({ token: savedToken });
    try {
      await apiFetch('/auth/verify');
      set({ isAuthenticated: true, isBackendOffline: false });
    } catch (err) {
      const e = err as Error;
      if (e instanceof ApiError || e.name === 'AbortError' || e.name === 'TypeError') {
        await get().checkBackendHealth();
      }
      set({ isAuthenticated: false, token: null });
      localStorage.removeItem('auth_token');
    }
  },

  checkBackendHealth: async () => {
    try {
      const res = await fetchWithTimeout(`${RAW_API_BASE}/api/health`, {}, 3000);
      if (res.ok) {
        set({ isBackendOffline: false });
      } else {
        set({ isBackendOffline: true });
      }
    } catch {
      set({ isBackendOffline: true });
    }
  },
}));
