import { create } from 'zustand';
import { apiFetch, type ProfileMeta, type GlobalSearchResult, type RagChatError, ApiError } from './api';
import { useStatusStore } from './statusStore';
import { useContactsStore } from './contactsStore';

interface RagState {
  savedProfile: string | null;
  profileMeta: ProfileMeta | null;
  isGeneratingProfile: boolean;
  isQueryingRAG: boolean;
  ragChatHistory: { sender: 'user' | 'ai'; text: string; time: string; error?: RagChatError }[];
  isGlobalSearchOpen: boolean;
  globalSearchQuery: string;
  globalSearchResults: GlobalSearchResult[];
  activeSearchController: AbortController | null;

  setGlobalSearchOpen: (open: boolean) => void;
  setGlobalSearchQuery: (query: string) => void;
  clearRagHistory: () => void;
  fetchProfile: (contact: string) => Promise<void>;
  generateProfile: (contact: string, startMonth: string, endMonth: string, forceCloud: boolean, deepScan: boolean, userConsent: boolean) => Promise<void>;
  queryRAG: (contact: string, query: string, startMonth: string | null, endMonth: string | null, deepScan: boolean, userConsent: boolean) => Promise<void>;
  globalSearch: (query: string) => Promise<void>;
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

  setGlobalSearchOpen: (isGlobalSearchOpen) => set({ isGlobalSearchOpen }),
  setGlobalSearchQuery: (globalSearchQuery) => set({ globalSearchQuery }),
  clearRagHistory: () => set({ ragChatHistory: [] }),

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

  generateProfile: async (contact, startMonth, endMonth, forceCloud, deepScan, userConsent) => {
    if (useContactsStore.getState().selectedContact !== contact) return;
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
      if (useContactsStore.getState().selectedContact !== contact) return;
      set({ savedProfile: data.profile, profileMeta: data.meta });
    } catch (err) {
      const e = err as Error;
      if (useContactsStore.getState().selectedContact !== contact) return;
      useStatusStore.getState().pushError(`Failed to generate profile: ${e.message}`, 'error');
    } finally {
      if (useContactsStore.getState().selectedContact === contact) {
        set({ isGeneratingProfile: false });
      }
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
      if (useContactsStore.getState().selectedContact !== contact) return;
      const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      set((state) => ({
        ragChatHistory: [...state.ragChatHistory, { sender: 'ai', text: data.response, time: responseTimeStr }],
      }));
    } catch (err) {
      const e = err as ApiError;
      if (useContactsStore.getState().selectedContact !== contact) return;
      useStatusStore.getState().pushError(`RAG query failed: ${e.message}`, 'error');
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
