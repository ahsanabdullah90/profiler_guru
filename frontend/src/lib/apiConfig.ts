/**
 * apiConfig.ts — Zero-dependency API primitives.
 *
 * This module intentionally has NO imports from any store or other
 * application module. It exports network constants, utility functions,
 * and a lightweight token-provider bridge that allows api.ts to obtain
 * the current JWT without creating a circular dependency on authStore.ts.
 *
 * Import graph rules:
 *   - api.ts, authStore.ts, statusStore.ts → MAY import from here
 *   - This file → MUST NOT import from any store or from api.ts
 */

// ── Network Constants ────────────────────────────────────────────────────────

/** Backend FastAPI port. */
export const API_PORT = 8_000;

/** API version prefix segment. */
export const API_VERSION = 'v1';

/** Timeout (ms) for paginated contact-list fetches. */
export const CONTACTS_FETCH_TIMEOUT = 60_000;

/** Default timeout (ms) for lightweight one-shot fetches. */
export const DEFAULT_FETCH_TIMEOUT = 5_000;

// ── Base URL Helpers ─────────────────────────────────────────────────────────

/**
 * Returns the fully-qualified API base URL at call time.
 * Uses window.location.hostname so the app works on any LAN address.
 */
export const getApiBase = (): string => {
  if (typeof window === 'undefined') {
    return `http://127.0.0.1:${API_PORT}/api/${API_VERSION}`;
  }
  return `http://${window.location.hostname}:${API_PORT}/api/${API_VERSION}`;
};

// ── Fetch Utilities ──────────────────────────────────────────────────────────

/**
 * Thin fetch wrapper that aborts after `timeout` milliseconds.
 * Used by authStore.checkBackendHealth and statusStore.pushError.
 */
export async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout = DEFAULT_FETCH_TIMEOUT,
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

// ── Token Provider Bridge ────────────────────────────────────────────────────
// Breaks the circular import: api.ts ↔ authStore.ts
// authStore registers a getter; api.ts reads it without importing authStore.

type TokenProvider = () => string | null;
let _tokenProvider: TokenProvider | null = null;

/**
 * Called once by authStore during store creation to register the JWT getter.
 * After registration, getAuthToken() returns the live token at call time.
 */
export function registerTokenProvider(fn: TokenProvider): void {
  _tokenProvider = fn;
}

/** Returns the current JWT token, or null if not yet authenticated. */
export function getAuthToken(): string | null {
  return _tokenProvider ? _tokenProvider() : null;
}

// ── Auth-Expiry Callback Bridge ──────────────────────────────────────────────
// Breaks the circular import: api.ts needing to call authStore.setAuthenticated

type AuthExpiredCallback = () => void;
let _onAuthExpired: AuthExpiredCallback | null = null;

/**
 * Called once by authStore during store creation to register the session-expiry
 * handler. When api.ts receives a 401 it calls triggerAuthExpired() instead of
 * importing authStore directly.
 */
export function registerAuthExpiredCallback(fn: AuthExpiredCallback): void {
  _onAuthExpired = fn;
}

/** Signals that the current session has expired. Calls authStore.setAuthenticated(false, null). */
export function triggerAuthExpired(): void {
  _onAuthExpired?.();
}

// ── Shared Type Definitions ──────────────────────────────────────────────────
// Defined here (not in api.ts) so statusStore.ts can import them without
// creating a circular dependency on api.ts.

export interface AppError {
  id: string;
  message: string;
  type: 'error' | 'warning' | 'info';
  timestamp: number;
}

export interface SystemStatus {
  app_online: boolean;
  transcription: {
    status: 'idle' | 'transcribing';
    contact: string;
    current: number;
    total: number;
  };
  rag: {
    status: 'idle' | 'indexing' | 'needs_indexing';
    contact: string;
    progress: number;
    warning?: string;
  };
  online_llm: {
    model: string;
    online: boolean;
  };
  ollama: {
    model: string;
    online: boolean;
  };
}

