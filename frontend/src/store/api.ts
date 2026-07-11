import { z } from 'zod';
import {
  getApiBase,
  getAuthToken,
  triggerAuthExpired,
  fetchWithTimeout,
  API_PORT,
  API_VERSION,
} from '../lib/apiConfig';

export interface Contact {
  name: string;
  client_id?: string | null;
  needs_migration?: boolean;
  display_name?: string | null;
  email?: string | null;
  mobile?: string | null;
  whatsapp?: string | null;
  instagram_handle?: string | null;
  photo_url?: string | null;
  platforms?: string[];
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
  audio_status: 'pending' | 'transcribed' | 'failed' | null;
  is_self: boolean;
  has_username_config?: boolean;
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

// SystemStatus and AppError live in apiConfig.ts (zero-dep module).
// Re-exported here so existing imports of these types from api.ts continue to work.
export type { SystemStatus, AppError } from '../lib/apiConfig';

export interface ProfileMeta {
  start_month: string;
  end_month: string;
  provider: string;
  model: string;
  generated_at: string;
  model_provider?: string | null;
  model_name?: string | null;
  framework_id?: string;
  scores?: Record<string, number> | null;
  classification?: string | null;
  pipeline_mode?: string;
  total_steps?: number;
}

export interface AssessmentHistoryEntry {
  history_id: number;
  framework_id: string;
  generated_at: string;
  scores: Record<string, number> | null;
  classification: string | null;
  pipeline_mode: string;
  model_name: string;
  summary: string | null;
  framework_version?: string | null;
}

export interface AvailableModel {
  provider: string;
  model: string;
  label: string;
  is_cloud: boolean;
}

export interface ModelListResponse {
  models: AvailableModel[];
  errors: Record<string, string>;
  cached_at: number;
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


// Re-export so existing callers of api.ts continue to work unchanged.
export { getApiBase, fetchWithTimeout } from '../lib/apiConfig';

const API_BASE = typeof window === 'undefined'
  ? `http://127.0.0.1:${API_PORT}/api/${API_VERSION}`
  : `http://${window.location.hostname}:${API_PORT}/api/${API_VERSION}`;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function fetchModels(): Promise<ModelListResponse> {
  return apiFetch<ModelListResponse>('/models');
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { schema?: z.ZodType<T>; timeout?: number } = {},
  retries = 2,
): Promise<T> {
  const { schema, timeout, ...fetchOptions } = options;
  const timeoutMs = timeout ?? 15000;
  const token = getAuthToken();
  const headers = new Headers(fetchOptions.headers);
  // Don't set Content-Type for FormData — browser sets multipart boundary automatically
  if (!(fetchOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const method = fetchOptions.method || 'GET';
  let idempotencyKey: string | null = null;
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method.toUpperCase())) {
    idempotencyKey = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  const controller = new AbortController();
  let timedOut = false;
  const timeoutId = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  
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
        triggerAuthExpired();
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
          throw new ValidationError(issues);
        }
        return result.data;
      }
      return data;
    } catch (err) {
      const e = err as Error;
      clearTimeout(timeoutId);
      if (e instanceof AuthError || e instanceof ApiError || e instanceof ValidationError) throw e;
      // Only retry on network errors (TypeError) or timeout aborts — not user-initiated aborts
      if (e.name === 'AbortError' && !timedOut) throw e;
      if (e.name !== 'TypeError' && e.name !== 'AbortError') throw e;
      if (attempt === retries) throw e;
      const baseDelay = 2 ** attempt * 1000;
      const jitter = Math.random() * 1000;
      // Surface retry notification
      if (attempt === 0) {
        import('./statusStore').then(({ useStatusStore }) => {
          useStatusStore.getState().pushError(`Retrying request...`, 'info');
        });
      }
      await sleep(baseDelay + jitter);
    }
  }
  throw new Error('Max retries exceeded');
}
