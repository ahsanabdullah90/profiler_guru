import { create } from 'zustand';
import { apiFetch, type ProfileMeta, type GlobalSearchResult, type RagChatError, getApiBase } from './api';
import { useStatusStore } from './statusStore';
import { useContactsStore } from './contactsStore';
import { useAuthStore } from './authStore';

interface RagState {
  savedProfile: string | null;
  profileMeta: ProfileMeta | null;
  isGeneratingProfile: boolean;
  isQueryingRAG: boolean;
  ragChatHistory: { sender: 'user' | 'ai'; text: string; time: string; error?: RagChatError; sources?: string[] }[];
  isGlobalSearchOpen: boolean;
  globalSearchQuery: string;
  globalSearchResults: GlobalSearchResult[];
  activeSearchController: AbortController | null;
  activeProfileController: AbortController | null;

  setGlobalSearchOpen: (open: boolean) => void;
  setGlobalSearchQuery: (query: string) => void;
  fetchProfile: (contact: string) => Promise<void>;
  generateProfile: (contact: string, startMonth: string, endMonth: string, forceCloud: boolean, deepScan: boolean, userConsent: boolean, modelProvider?: string, modelName?: string, frameworkId?: string) => Promise<void>;
  queryRAG: (contact: string, query: string, startMonth: string | null, endMonth: string | null, deepScan: boolean, userConsent: boolean) => Promise<void>;
  globalSearch: (query: string) => Promise<void>;
  clearProfile: () => void;
  cancelProfileGeneration: () => void;
}

export const useRagStore = create<RagState>((set, get) => ({
  savedProfile: null,
  profileMeta: null,
  isGeneratingProfile: false,
  isQueryingRAG: false,
  ragChatHistory: [],
  isGlobalSearchOpen: false,
  globalSearchQuery: '',
  globalSearchResults: [],
  activeSearchController: null,
  activeProfileController: null,

  setGlobalSearchOpen: (isGlobalSearchOpen) => set({ isGlobalSearchOpen }),
  setGlobalSearchQuery: (globalSearchQuery) => set({ globalSearchQuery }),
  clearProfile: () => set({ savedProfile: null, profileMeta: null }),

  fetchProfile: async (contact) => {
    const signal = useContactsStore.getState().activeContactController?.signal;
    try {
      const data = await apiFetch<{ profile: string | null; meta: ProfileMeta | null }>(`/rag/contacts/${contact}/profile`, { signal });
      if (useContactsStore.getState().selectedContact !== contact) return;
      set({ savedProfile: data.profile, profileMeta: data.meta });
    } catch (err) {
      const e = err as Error;
      if (e.name === 'AbortError') return;
      if (useContactsStore.getState().selectedContact !== contact) return;
      useStatusStore.getState().pushError(`Failed to load profile for ${contact}: ${e.message}`, 'warning');
    }
  },

  generateProfile: async (contact, startMonth, endMonth, forceCloud, deepScan, userConsent, modelProvider?, modelName?, frameworkId?) => {
    if (useContactsStore.getState().selectedContact !== contact) return;
    const controller = new AbortController();
    set({ isGeneratingProfile: true, activeProfileController: controller });
    try {
      const body: Record<string, unknown> = {
        start_month: startMonth,
        end_month: endMonth,
        user_consent: userConsent,
        framework_id: frameworkId || 'communication_style',
      };
      if (modelProvider && modelName) {
        body.model_provider = modelProvider;
        body.model_name = modelName;
      } else {
        body.force_cloud = forceCloud ?? false;
        body.deep_scan = false;
      }
      const data = await apiFetch<{ profile: string; meta: ProfileMeta }>(`/rag/contacts/${contact}/profile`, {
        method: 'POST',
        body: JSON.stringify(body),
        timeout: 300000,
        signal: controller.signal,
      });
      if (useContactsStore.getState().selectedContact !== contact) return;
      set({ savedProfile: data.profile, profileMeta: data.meta });
    } catch (err) {
      const e = err as Error;
      if (e.name === 'AbortError') return;
      if (useContactsStore.getState().selectedContact !== contact) return;
      useStatusStore.getState().pushError(`Failed to generate profile: ${e.message}`, 'error');
    } finally {
      if (useContactsStore.getState().selectedContact === contact) {
        set({ isGeneratingProfile: false, activeProfileController: null });
      }
    }
  },

  cancelProfileGeneration: () => {
    const controller = get().activeProfileController;
    if (controller) {
      controller.abort();
      set({ activeProfileController: null, isGeneratingProfile: false });
    }
  },

  queryRAG: async (contact, query, startMonth, endMonth, deepScan, userConsent) => {
    if (useContactsStore.getState().selectedContact !== contact) return;
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    set((state) => ({
      isQueryingRAG: true,
      ragChatHistory: [...state.ragChatHistory, { sender: 'user', text: query, time: timeStr }],
    }));

    try {
      const token = useAuthStore.getState().token;
      const apiBase = getApiBase();
      const response = await fetch(`${apiBase}/rag/contacts/${contact}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          query,
          start_month: startMonth,
          end_month: endMonth,
          deep_scan: deepScan,
          user_consent: userConsent,
        }),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson?.detail?.message || errJson?.detail || response.statusText);
      }

      if (!response.body) {
        throw new Error("No response body received from stream.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentAiMsgIndex = -1;
      
      const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      set((state) => {
        const nextHistory = [...state.ragChatHistory, { sender: 'ai' as const, text: '', time: responseTimeStr, sources: [] }];
        currentAiMsgIndex = nextHistory.length - 1;
        return { ragChatHistory: nextHistory };
      });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;
          const dataStr = trimmed.slice(6);
          if (dataStr === '{"type": "done"}') continue;

          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.type === 'metadata') {
              set((state) => {
                if (currentAiMsgIndex === -1) return {};
                const nextHistory = [...state.ragChatHistory];
                const msg = nextHistory[currentAiMsgIndex];
                if (msg) {
                  msg.sources = parsed.sources || [];
                }
                return { ragChatHistory: nextHistory };
              });
            } else if (parsed.type === 'token') {
              set((state) => {
                if (currentAiMsgIndex === -1) return {};
                const nextHistory = [...state.ragChatHistory];
                const msg = nextHistory[currentAiMsgIndex];
                if (msg) {
                  msg.text += parsed.text;
                }
                return { ragChatHistory: nextHistory };
              });
            } else if (parsed.type === 'error') {
              throw new Error(parsed.message || 'Stream error');
            }
          } catch {
            // Ignore unparseable SSE lines
          }
        }
      }
    } catch (err) {
      const e = err as Error;
      if (useContactsStore.getState().selectedContact !== contact) return;
      useStatusStore.getState().pushError(`RAG query failed: ${e.message}`, 'error');
      const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      
      set((state) => {
        const nextHistory = [...state.ragChatHistory];
        const lastMsg = nextHistory[nextHistory.length - 1];
        if (lastMsg && lastMsg.sender === 'ai' && !lastMsg.error) {
          lastMsg.text = e.message || 'LLM query failed.';
          lastMsg.error = {
            message: e.message || 'LLM query failed.',
            can_retry: true,
            query,
            start_month: startMonth,
            end_month: endMonth,
            deep_scan: deepScan,
            user_consent: userConsent
          };
          return { ragChatHistory: nextHistory };
        } else {
          return {
            ragChatHistory: [
              ...nextHistory,
              {
                sender: 'ai' as const,
                text: e.message || 'LLM query failed.',
                time: responseTimeStr,
                error: {
                  message: e.message || 'LLM query failed.',
                  can_retry: true,
                  query,
                  start_month: startMonth,
                  end_month: endMonth,
                  deep_scan: deepScan,
                  user_consent: userConsent
                }
              }
            ]
          };
        }
      });
    } finally {
      if (useContactsStore.getState().selectedContact === contact) {
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
      useStatusStore.getState().pushError(`Global search failed: ${e.message}`, 'warning');
    } finally {
      if (get().activeSearchController === newController) {
        set({ activeSearchController: null });
      }
    }
  },
}));
