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

export interface ProfileMeta {
  start_month: string;
  end_month: string;
  provider: string;
  model: string;
  generated_at: string;
}

export interface GlobalSearchResult {
  id: string;
  document: string;
  chat_name: string;
  month: string;
  date_range: string;
}

export interface RagChatError {
  message: string;
  can_retry: boolean;
  query: string;
  start_month: string | null;
  end_month: string | null;
  deep_scan: boolean;
  user_consent: boolean;
}

export class AuthError extends Error {
  constructor(msg: string) { super(msg); this.name = 'AuthError'; }
}

export class ApiError extends Error {
  status: number;
  data: Record<string, unknown> | null = null;
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

const API_BASE = typeof window === 'undefined'
  ? `http://127.0.0.1:8000/api/${API_VERSION}`
  : `http://${window.location.hostname}:8000/api/${API_VERSION}`;

const RAW_API_BASE = API_BASE.replace(`/${API_VERSION}`, '');

/** Sleep helper for retry backoff */
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Custom fetch wrapper with a timeout. */
export async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = 5000): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

/** Default fetch wrapper with JWT auth, timeout, and retry logic. */
export async function apiFetch<T>(
  path: string,
  options: RequestInit & { schema?: z.ZodType<T>; timeout?: number } = {},
  retries = 2,
): Promise<T> {
  const { schema, timeout, ...fetchOptions } = options;
  const timeoutMs = timeout ?? 15000;
  const token = useSyncStore.getState().token;
  const headers = new Headers(fetchOptions.headers);
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const method = fetchOptions.method || 'GET';
  let idempotencyKey: string | null = null;
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method.toUpperCase())) {
    idempotencyKey = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  const abortSignalClass = AbortSignal as unknown as { any?: (signals: AbortSignal[]) => AbortSignal };
  const signal = fetchOptions.signal
    ? (abortSignalClass.any
      ? abortSignalClass.any([fetchOptions.signal, controller.signal])
      : fetchOptions.signal)
    : controller.signal;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      if (idempotencyKey) {
        headers.set('Idempotency-Key', idempotencyKey);
      }
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
        const detail = err.detail;
        let message = '';
        let errorData: Record<string, unknown> | null = null;
        
        if (typeof detail === 'object' && detail !== null) {
          const detailObj = detail as Record<string, unknown>;
          message = (detailObj.message as string) || (detailObj.error as string) || JSON.stringify(detailObj);
          errorData = detailObj;
        } else {
          message = detail || res.statusText;
        }
        
        const apiError = new ApiError(res.status, message);
        if (errorData) {
          apiError.data = errorData;
        }
        throw apiError;
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
    } catch (err) {
      const e = err as Error;
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
  profileMeta: ProfileMeta | null;
  activeTab: 'chat' | 'analytics';
  searchQuery: string;

  isGeneratingProfile: boolean;
  isQueryingRAG: boolean;
  ragChatHistory: { sender: 'user' | 'ai'; text: string; time: string; error?: RagChatError }[];

  isGlobalSearchOpen: boolean;
  globalSearchQuery: string;
  globalSearchResults: GlobalSearchResult[];

  status: SystemStatus;
  errors: AppError[];
  activeContactController: AbortController | null;
  activeSearchController: AbortController | null;
  
  isBackendOffline: boolean;
  contactTotal: number;
  contactPage: number;
  contactPages: number;
  messageTotal: number;
  messagePage: number;
  messagePages: number;

  pushError: (message: string, type?: AppError['type']) => void;
  dismissError: (id: string) => void;
  setAuthenticated: (auth: boolean, token: string | null) => void;
  verifyToken: () => Promise<void>;
  checkBackendHealth: () => Promise<void>;
  setSelectedContact: (contact: string | null) => void;
  setSelectedMonth: (month: string | null) => void;
  setActiveTab: (tab: 'chat' | 'analytics') => void;
  setSearchQuery: (query: string) => void;
  setGlobalSearchOpen: (open: boolean) => void;
  setGlobalSearchQuery: (query: string) => void;
  clearRagHistory: () => void;
  setStatus: (status: Partial<SystemStatus>) => void;

  login: (password: string) => Promise<boolean>;

  fetchContacts: (opts?: { page?: number; limit?: number; search?: string }) => Promise<void>;
  fetchMonths: (contact: string) => Promise<void>;
  fetchMessages: (contact: string, month: string, opts?: { page?: number; limit?: number }) => Promise<void>;
  fetchAnalytics: (contact: string) => Promise<void>;
  fetchProfile: (contact: string) => Promise<void>;
  generateProfile: (contact: string, startMonth: string, endMonth: string, forceCloud: boolean, deepScan: boolean, userConsent: boolean) => Promise<void>;
  queryRAG: (contact: string, query: string, startMonth: string | null, endMonth: string | null, deepScan: boolean, userConsent: boolean) => Promise<void>;
  globalSearch: (query: string) => Promise<void>;
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
  
  isBackendOffline: false,
  contactTotal: 0,
  contactPage: 1,
  contactPages: 1,
  messageTotal: 0,
  messagePage: 1,
  messagePages: 1,

  status: {
    app_online: false,
    instagram_sync: { status: 'idle', contact: '', current: 0, total: 0 },
    transcription: { status: 'idle', contact: '', current: 0, total: 0 },
    rag: { status: 'idle', contact: '', progress: 100 },
    online_llm: { model: 'Gemini 1.5 Flash', online: false },
    ollama: { model: 'None', online: false },
  },
  errors: [],
  activeContactController: null,
  activeSearchController: null,

  pushError: (message, type = 'error') => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const error: AppError = { id, message, type, timestamp: Date.now() };
    set((state) => ({ errors: [...state.errors, error] }));
    // Auto-dismiss after 8 seconds
    setTimeout(() => {
      get().dismissError(id);
    }, 8000);

    // Report error to backend logs in the background
    const apiBase = getApiBase();
    fetchWithTimeout(`${apiBase.replace('/v1', '')}/v1/logs/frontend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        url: typeof window !== 'undefined' ? window.location.href : 'unknown',
        timestamp: Date.now(),
        type,
      }),
    }, 5000).catch(() => {});
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
    const win = window as unknown as { _global_error_registered?: boolean };
    if (typeof window !== 'undefined' && !win._global_error_registered) {
      win._global_error_registered = true;
      window.addEventListener('error', (event) => {
        get().pushError(`Unhandled error: ${event.message}`, 'error');
      });
      window.addEventListener('unhandledrejection', (event) => {
        const reason = event.reason;
        const msg = reason instanceof Error ? reason.message : String(reason);
        get().pushError(`Promise rejection: ${msg}`, 'error');
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
        // If it's a network/server crash, run health check
        await get().checkBackendHealth();
      }
      set({ isAuthenticated: false, token: null });
      localStorage.removeItem('auth_token');
    }
  },

  checkBackendHealth: async () => {
    try {
      const res = await fetchWithTimeout(`${RAW_API_BASE}/health`, {}, 3000);
      if (res.ok) {
        set({ isBackendOffline: false });
      } else {
        set({ isBackendOffline: true });
      }
    } catch {
      set({ isBackendOffline: true });
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
    } catch (err) {
      const e = err as Error;
      get().pushError(`Login failed: ${e.message}`, 'error');
      throw e;
    }
  },

  setSelectedContact: (contact) => {
    // Abort in-flight details requests for previous contact
    const currentController = get().activeContactController;
    if (currentController) {
      currentController.abort();
    }
    const newController = new AbortController();

    set({
      selectedContact: contact,
      selectedMonth: null,
      availableMonths: [],
      messages: [],
      analytics: null,
      savedProfile: null,
      profileMeta: null,
      ragChatHistory: [],
      activeContactController: newController,
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
  setStatus: (newStatus) => set((state) => {
    const merged = { ...state.status } as unknown as Record<string, unknown>;
    const statusObj = newStatus as Record<string, unknown>;
    for (const key in newStatus) {
      const val = statusObj[key];
      if (val && typeof val === 'object' && !Array.isArray(val)) {
        merged[key] = { ...(merged[key] as Record<string, unknown>), ...(val as Record<string, unknown>) };
      } else {
        merged[key] = val;
      }
    }
    return { status: merged as unknown as SystemStatus };
  }),

  fetchContacts: async (opts?: { page?: number; limit?: number; search?: string }) => {
    try {
      const page = opts?.page ?? 1;
      const limit = opts?.limit ?? 50;
      const search = opts?.search ?? '';
      const params = new URLSearchParams({ page: String(page), limit: String(limit) });
      if (search) params.set('search', search);
      const data = await apiFetch<{ contacts: Contact[]; total: number; page: number; pages: number }>(
        `/contacts?${params}`,
        { timeout: 60000 },
      );
      set({
        contacts: data.contacts,
        contactTotal: data.total,
        contactPage: data.page,
        contactPages: data.pages,
      });
    } catch (err) {
      const e = err as Error;
      get().pushError(`Failed to load contacts: ${e.message}`, 'error');
    }
  },

  fetchMonths: async (contact) => {
    const signal = get().activeContactController?.signal;
    try {
      const data = await apiFetch<string[]>(`/contacts/${contact}/months`, { signal });
      if (get().selectedContact !== contact) return;
      set({ availableMonths: data });
      if (data.length > 0) {
        get().setSelectedMonth(data[0]);
      }
    } catch (err) {
      const e = err as Error;
      if (e.name === 'AbortError') return;
      if (get().selectedContact !== contact) return;
      get().pushError(`Failed to load months for ${contact}: ${e.message}`, 'error');
    }
  },

  fetchMessages: async (contact, month, opts) => {
    const signal = get().activeContactController?.signal;
    try {
      const page = opts?.page ?? 1;
      const limit = opts?.limit ?? 100;
      const params = new URLSearchParams({ page: String(page), limit: String(limit) });
      const data = await apiFetch<{ messages: Message[]; total: number; page: number; pages: number }>(
        `/contacts/${contact}/messages/${month}?${params}`,
        { signal },
      );
      if (get().selectedContact !== contact || get().selectedMonth !== month) return;
      set({
        messages: data.messages,
        messageTotal: data.total,
        messagePage: data.page,
        messagePages: data.pages,
      });
    } catch (err) {
      const e = err as Error;
      if (e.name === 'AbortError') return;
      if (get().selectedContact !== contact || get().selectedMonth !== month) return;
      get().pushError(`Failed to load messages: ${e.message}`, 'error');
    }
  },

  fetchAnalytics: async (contact) => {
    const signal = get().activeContactController?.signal;
    try {
      const data = await apiFetch<Analytics>(`/contacts/${contact}/analytics`, { signal });
      if (get().selectedContact !== contact) return;
      set({ analytics: data });
    } catch (err) {
      const e = err as Error;
      if (e.name === 'AbortError') return;
      if (get().selectedContact !== contact) return;
      get().pushError(`Failed to load analytics for ${contact}: ${e.message}`, 'error');
    }
  },

  fetchProfile: async (contact) => {
    const signal = get().activeContactController?.signal;
    try {
      const data = await apiFetch<{ profile: string | null; meta: ProfileMeta | null }>(`/rag/contacts/${contact}/profile`, { signal });
      if (get().selectedContact !== contact) return;
      set({ savedProfile: data.profile, profileMeta: data.meta });
    } catch (err) {
      const e = err as Error;
      if (e.name === 'AbortError') return;
      if (get().selectedContact !== contact) return;
      get().pushError(`Failed to load profile for ${contact}: ${e.message}`, 'warning');
    }
  },

  generateProfile: async (contact, startMonth, endMonth, forceCloud, deepScan, userConsent) => {
    if (get().selectedContact !== contact) return;
    set({ isGeneratingProfile: true });
    try {
      const data = await apiFetch<{ profile: string; meta: ProfileMeta }>(`/rag/contacts/${contact}/profile`, {
        method: 'POST',
        body: JSON.stringify({
          start_month: startMonth,
          end_month: endMonth,
          force_cloud: forceCloud,
          deep_scan: deepScan,
          user_consent: userConsent,
        }),
      });
      if (get().selectedContact !== contact) return;
      set({ savedProfile: data.profile, profileMeta: data.meta });
    } catch (err) {
      const e = err as Error;
      if (get().selectedContact !== contact) return;
      get().pushError(`Failed to generate profile: ${e.message}`, 'error');
    } finally {
      if (get().selectedContact === contact) {
        set({ isGeneratingProfile: false });
      }
    }
  },

  queryRAG: async (contact, query, startMonth, endMonth, deepScan, userConsent) => {
    if (get().selectedContact !== contact) return;
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
      if (get().selectedContact !== contact) return;
      const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      set((state) => ({
        ragChatHistory: [...state.ragChatHistory, { sender: 'ai', text: data.response, time: responseTimeStr }],
      }));
    } catch (err) {
      const e = err as ApiError;
      if (get().selectedContact !== contact) return;
      get().pushError(`RAG query failed: ${e.message}`, 'error');
      const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const errorData = e.data || null;
      
      const errorPayload = errorData ? {
        message: (errorData.message as string) || e.message || 'LLM query failed.',
        can_retry: typeof errorData.can_retry === 'boolean' ? errorData.can_retry : true,
        query,
        start_month: startMonth,
        end_month: endMonth,
        deep_scan: deepScan,
        user_consent: userConsent
      } : {
        message: e.message || 'LLM query failed.',
        can_retry: true,
        query,
        start_month: startMonth,
        end_month: endMonth,
        deep_scan: deepScan,
        user_consent: userConsent
      };

      set((state) => ({
        ragChatHistory: [
          ...state.ragChatHistory,
          { 
            sender: 'ai', 
            text: e.message, 
            time: responseTimeStr,
            error: errorPayload
          },
        ],
      }));
    } finally {
      if (get().selectedContact === contact) {
        set({ isQueryingRAG: false });
      }
    }
  },

  globalSearch: async (query) => {
    const currentController = get().activeSearchController;
    if (currentController) {
      currentController.abort();
    }

    if (!query.trim()) {
      set({ globalSearchResults: [], activeSearchController: null });
      return;
    }

    const newController = new AbortController();
    set({ activeSearchController: newController });

    try {
      const data = await apiFetch<GlobalSearchResult[]>('/rag/search', {
        method: 'POST',
        body: JSON.stringify({ query }),
        signal: newController.signal,
      });
      if (get().globalSearchQuery !== query) return;
      set({ globalSearchResults: data });
    } catch (err) {
      const e = err as Error;
      if (e.name === 'AbortError') return;
      if (get().globalSearchQuery !== query) return;
      get().pushError(`Global search failed: ${e.message}`, 'warning');
    } finally {
      if (get().activeSearchController === newController) {
        set({ activeSearchController: null });
      }
    }
  },

  triggerInstagramSync: async () => {
    try {
      await apiFetch('/instagram/sync/once', { method: 'POST' });
      return true;
    } catch (err) {
      const e = err as Error;
      get().pushError(`Failed to trigger Instagram sync: ${e.message}`, 'error');
      return false;
    }
  },

  toggleDaemonSync: async () => {
    try {
      const data = await apiFetch<{ daemon_sync_active: boolean }>('/instagram/sync/toggle', { method: 'POST' });
      return data.daemon_sync_active;
    } catch (err) {
      const e = err as Error;
      get().pushError(`Failed to toggle daemon sync: ${e.message}`, 'error');
      return false;
    }
  },
}));

