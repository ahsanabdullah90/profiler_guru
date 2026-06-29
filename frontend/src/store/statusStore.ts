import { create } from 'zustand';
import { type SystemStatus, type AppError, getApiBase, fetchWithTimeout } from './api';

interface StatusState {
  status: SystemStatus;
  errors: AppError[];

  setStatus: (newStatus: Partial<SystemStatus>) => void;
  pushError: (message: string, type?: AppError['type']) => void;
  dismissError: (id: string) => void;
}

export const useStatusStore = create<StatusState>((set, get) => ({
  status: {
    app_online: false,
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
    setTimeout(() => {
      get().dismissError(id);
    }, 8000);

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

  setStatus: (newStatus) => set((state) => {
    const merged = { ...state.status } as Record<string, unknown>;
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
}));
