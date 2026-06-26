import { create } from 'zustand';
import { z } from 'zod';

export interface Contact {
  name: string;
  msg_count: number;
  last_date: string;
  last_snippet: string;
  avg_msg: number;
  indexed_chunks: number;
  rag_progress: number;
  depth_label: string;
  depth_color: string;
}

export interface Message {
  id: string;
  sender: string;
  time: string;
  text: string;
  audio_url: string | null;
  is_self: boolean;
}

export interface Analytics {
  avg_msg_weekly: number;
  avg_msg_monthly: number;
  depth_label: string;
  depth_color: string;
  timeline: { date: string; messages: number }[];
  total_messages: number;
  audio_count: number;
  audio_ratio: number;
}

export interface SystemStatus {
  app_online: boolean;
  instagram_sync: {
    status: 'idle' | 'syncing';
    contact: string;
    current: number;
    total: number;
  };
  transcription: {
    status: 'idle' | 'transcribing';
    contact: string;
    current: number;
    total: number;
  };
  rag: {
    status: 'idle' | 'indexing';
    contact: string;
    progress: number;
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

export class AuthError extends Error {
  constructor(msg: string) { super(msg); this.name = 'AuthError'; }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, msg: string) {
    super(msg);
    this.name = 'ApiError';
    this.status = status;
  }
}

export class ValidationError extends Error {
  issues: Array<{ path: string; message: string }>;
  constructor(issues: Array<{ path: string; message: string }>) {
    super('Response validation failed');
    this.name = 'ValidationError';
    this.issues = issues;
  }
}

export interface AppError {
  id: string;
  message: string;
  type: 'error' | 'warning' | 'info';
  timestamp: number;
}

// ---- API helpers ----

const API_VERSION = 'v1';

export const getApiBase = () => {
  if (typeof window === 'undefined') return `http://127.0.0.1:8000/api/${API_VERSION}`;
  return `http://${window.location.hostname}:8000/api/${API_VERSION}`;
};

export const getWsUrl = () => {
  if (typeof window === 'undefined') return 'ws://127.0.0.1:8000/ws/status';
  return `ws://${window.location.hostname}:8000/ws/status`;
};

const API_BASE = typeof window === 'undefined'
  ? `http://127.0.0.1:8000/api/${API_VERSION}`
  : `http://${window.location.hostname}:8000/api/${API_VERSION}`;

const RAW_API_BASE = API_BASE.replace(`/${API_VERSION}`, '');

/** Sleep helper for retry backoff */
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Default fetch wrapper with JWT auth, timeout, and retry logic. */
export async function apiFetch<T>(
  path: string,
  options: RequestInit & { schema?: z.ZodType<T> } = {},
  retries = 2,
): Promise<T> {
  const { schema, ...fetchOptions } = options;
  const token = useSyncStore.getState().token;
  const headers = new Headers(fetchOptions.headers);
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  const signal = fetchOptions.signal
    ? (AbortSignal as any).any
      ? (AbortSignal as any).any([fetchOptions.signal, controller.signal])
      : fetchOptions.signal
    : controller.signal;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        ...fetchOptions,
        headers,
        signal,
      });
      clearTimeout(timeoutId);

      if (res.status === 401) {
        useSyncStore.getState().setAuthenticated(false, null);
        throw new AuthError('Session expired');
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new ApiError(res.status, err.detail || res.statusText);
      }

      const data: T = res.status === 204 ? (undefined as T) : await res.json();
      if (schema) {
        const result = schema.safeParse(data);
        if (!result.success) {
          const issues = result.error.issues.map((i) => ({
            path: i.path.join('.'),
            message: i.message,
          }));
          console.error('[apiFetch] Schema validation failed:', issues);
          throw new ValidationError(issues);
        }
        return result.data;
      }
      return data;
    } catch (e: any) {
      clearTimeout(timeoutId);
      if (e instanceof AuthError || e instanceof ApiError || e instanceof ValidationError) throw e;
      // Only retry on network or abort errors; HTTP 4xx/5xx throw ApiError above
      if (e.name !== 'TypeError' && e.name !== 'AbortError') throw e;
      if (attempt === retries) throw e;
      const baseDelay = 2 ** attempt * 1000;
      const jitter = Math.random() * 1000;
      await sleep(baseDelay + jitter);
    }
  }
  throw new Error('Max retries exceeded');
}

/** Unauthenticated fetch (for status polling, health checks). */
export async function rawFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${RAW_API_BASE}${path}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// ---- Zustand State ----

interface SyncState {
  isAuthenticated: boolean;
  token: string | null;
  contacts: Contact[];
  selectedContact: string | null;
  selectedMonth: string | null;
  availableMonths: string[];
  messages: Message[];
  analytics: Analytics | null;
  savedProfile: string | null;
  profileMeta: any | null;
  activeTab: 'chat' | 'analytics';
  searchQuery: string;

  isGeneratingProfile: boolean;
  isQueryingRAG: boolean;
  ragChatHistory: { sender: 'user' | 'ai'; text: string; time: string }[];

  isGlobalSearchOpen: boolean;
  globalSearchQuery: string;
  globalSearchResults: any[];

  status: SystemStatus;
  errors: AppError[];

  pushError: (message: string, type?: AppError['type']) => void;
  dismissError: (id: string) => void;
  setAuthenticated: (auth: boolean, token: string | null) => void;
  verifyToken: () => Promise<void>;
  setSelectedContact: (contact: string | null) => void;
  setSelectedMonth: (month: string | null) => void;
  setActiveTab: (tab: 'chat' | 'analytics') => void;
  setSearchQuery: (query: string) => void;
  setGlobalSearchOpen: (open: boolean) => void;
  setGlobalSearchQuery: (query: string) => void;
  clearRagHistory: () => void;
  setStatus: (status: Partial<SystemStatus>) => void;

  login: (password: string) => Promise<boolean>;

  fetchContacts: () => Promise<void>;
  fetchMonths: (contact: string) => Promise<void>;
  fetchMessages: (contact: string, month: string) => Promise<void>;
  fetchAnalytics: (contact: string) => Promise<void>;
  fetchProfile: (contact: string) => Promise<void>;
  generateProfile: (contact: string, startMonth: string, endMonth: string, forceCloud: boolean, deepScan: boolean, userConsent: boolean) => Promise<void>;
  queryRAG: (contact: string, query: string, startMonth: string | null, endMonth: string | null, deepScan: boolean, userConsent: boolean) => Promise<void>;
  globalSearch: (query: string) => Promise<void>;
  logoutInstagram: () => Promise<void>;
  triggerInstagramSync: () => Promise<boolean>;
  toggleDaemonSync: () => Promise<boolean>;
}

export const useSyncStore = create<SyncState>((set, get) => ({
  isAuthenticated: false,
  token: null,
  contacts: [],
  selectedContact: null,
  selectedMonth: null,
  availableMonths: [],
  messages: [],
  analytics: null,
  savedProfile: null,
  profileMeta: null,
  activeTab: 'chat',
  searchQuery: '',

  isGeneratingProfile: false,
  isQueryingRAG: false,
  ragChatHistory: [],

  isGlobalSearchOpen: false,
  globalSearchQuery: '',
  globalSearchResults: [],

  status: {
    app_online: false,
    instagram_sync: { status: 'idle', contact: '', current: 0, total: 0 },
    transcription: { status: 'idle', contact: '', current: 0, total: 0 },
    rag: { status: 'idle', contact: '', progress: 100 },
    online_llm: { model: 'Gemini 1.5 Flash', online: false },
    ollama: { model: 'None', online: false },
  },
  errors: [],

  pushError: (message, type = 'error') => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const error: AppError = { id, message, type, timestamp: Date.now() };
    set((state) => ({ errors: [...state.errors, error] }));
    // Auto-dismiss after 8 seconds
    setTimeout(() => {
      get().dismissError(id);
    }, 8000);
  },

  dismissError: (id) => {
    set((state) => ({ errors: state.errors.filter((e) => e.id !== id) }));
  },

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

  verifyToken: async () => {
    const savedToken = localStorage.getItem('auth_token');
    if (!savedToken) {
      set({ isAuthenticated: false, token: null });
      return;
    }
    set({ token: savedToken });
    try {
      await apiFetch('/auth/verify');
      set({ isAuthenticated: true });
    } catch {
      set({ isAuthenticated: false, token: null });
      localStorage.removeItem('auth_token');
    }
  },

  login: async (password) => {
    try {
      const data = await apiFetch<{ token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
      });
      get().setAuthenticated(true, data.token);
      return true;
    } catch (e: any) {
      get().pushError(`Login failed: ${e.message}`, 'error');
      return false;
    }
  },

  setSelectedContact: (contact) => {
    set({
      selectedContact: contact,
      selectedMonth: null,
      availableMonths: [],
      messages: [],
      analytics: null,
      savedProfile: null,
      profileMeta: null,
      ragChatHistory: [],
    });
    if (contact) {
      get().fetchMonths(contact);
      get().fetchAnalytics(contact);
      get().fetchProfile(contact);
    }
  },

  setSelectedMonth: (month) => {
    set({ selectedMonth: month, messages: [] });
    const contact = get().selectedContact;
    if (contact && month) {
      get().fetchMessages(contact, month);
    }
  },

  setActiveTab: (activeTab) => set({ activeTab }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setGlobalSearchOpen: (isGlobalSearchOpen) => set({ isGlobalSearchOpen }),
  setGlobalSearchQuery: (globalSearchQuery) => set({ globalSearchQuery }),
  clearRagHistory: () => set({ ragChatHistory: [] }),
  setStatus: (newStatus) => set((state) => ({ status: { ...state.status, ...newStatus } })),

  fetchContacts: async () => {
    try {
      const data = await apiFetch<Contact[]>('/contacts');
      set({ contacts: data });
    } catch (e: any) {
      get().pushError(`Failed to load contacts: ${e.message}`, 'error');
    }
  },

  fetchMonths: async (contact) => {
    try {
      const data = await apiFetch<string[]>(`/contacts/${contact}/months`);
      set({ availableMonths: data });
      if (data.length > 0) {
        get().setSelectedMonth(data[0]);
      }
    } catch (e: any) {
      get().pushError(`Failed to load months for ${contact}: ${e.message}`, 'error');
    }
  },

  fetchMessages: async (contact, month) => {
    try {
      const data = await apiFetch<Message[]>(`/contacts/${contact}/messages/${month}`);
      set({ messages: data });
    } catch (e: any) {
      get().pushError(`Failed to load messages: ${e.message}`, 'error');
    }
  },

  fetchAnalytics: async (contact) => {
    try {
      const data = await apiFetch<Analytics>(`/contacts/${contact}/analytics`);
      set({ analytics: data });
    } catch (e: any) {
      get().pushError(`Failed to load analytics for ${contact}: ${e.message}`, 'error');
    }
  },

  fetchProfile: async (contact) => {
    try {
      const data = await apiFetch<{ profile: string | null; meta: any }>(`/rag/contacts/${contact}/profile`);
      set({ savedProfile: data.profile, profileMeta: data.meta });
    } catch (e: any) {
      get().pushError(`Failed to load profile for ${contact}: ${e.message}`, 'warning');
    }
  },

  generateProfile: async (contact, startMonth, endMonth, forceCloud, deepScan, userConsent) => {
    set({ isGeneratingProfile: true });
    try {
      const data = await apiFetch<{ profile: string; meta: any }>(`/rag/contacts/${contact}/profile`, {
        method: 'POST',
        body: JSON.stringify({
          start_month: startMonth,
          end_month: endMonth,
          force_cloud: forceCloud,
          deep_scan: deepScan,
          user_consent: userConsent,
        }),
      });
      set({ savedProfile: data.profile, profileMeta: data.meta });
    } catch (e: any) {
      get().pushError(`Failed to generate profile: ${e.message}`, 'error');
    } finally {
      set({ isGeneratingProfile: false });
    }
  },

  queryRAG: async (contact, query, startMonth, endMonth, deepScan, userConsent) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    set((state) => ({
      isQueryingRAG: true,
      ragChatHistory: [...state.ragChatHistory, { sender: 'user', text: query, time: timeStr }],
    }));

    try {
      const data = await apiFetch<{ response: string }>(`/rag/contacts/${contact}/query`, {
        method: 'POST',
        body: JSON.stringify({
          query,
          start_month: startMonth,
          end_month: endMonth,
          deep_scan: deepScan,
          user_consent: userConsent,
        }),
      });
      const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      set((state) => ({
        ragChatHistory: [...state.ragChatHistory, { sender: 'ai', text: data.response, time: responseTimeStr }],
      }));
    } catch (e: any) {
      get().pushError(`RAG query failed: ${e.message}`, 'error');
      const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      set((state) => ({
        ragChatHistory: [
          ...state.ragChatHistory,
          { sender: 'ai', text: `Error: RAG index query failed. Details: ${e.message}`, time: responseTimeStr },
        ],
      }));
    } finally {
      set({ isQueryingRAG: false });
    }
  },

  globalSearch: async (query) => {
    if (!query.trim()) {
      set({ globalSearchResults: [] });
      return;
    }
    try {
      const data = await apiFetch<any[]>('/rag/search', {
        method: 'POST',
        body: JSON.stringify({ query }),
      });
      set({ globalSearchResults: data });
    } catch (e: any) {
      get().pushError(`Global search failed: ${e.message}`, 'warning');
    }
  },

  logoutInstagram: async () => {
    /* no-op — session cleanup handled server-side */
  },

  triggerInstagramSync: async () => {
    try {
      await apiFetch('/instagram/sync/once', { method: 'POST' });
      return true;
    } catch (e: any) {
      get().pushError(`Failed to trigger Instagram sync: ${e.message}`, 'error');
      return false;
    }
  },

  toggleDaemonSync: async () => {
    try {
      const data = await apiFetch<{ daemon_sync_active: boolean }>('/instagram/sync/toggle', { method: 'POST' });
      return data.daemon_sync_active;
    } catch (e: any) {
      get().pushError(`Failed to toggle daemon sync: ${e.message}`, 'error');
      return false;
    }
  },
}));
