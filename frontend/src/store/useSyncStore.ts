import { create } from 'zustand';

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
  
  // AI Interactions
  isGeneratingProfile: boolean;
  isQueryingRAG: boolean;
  ragChatHistory: { sender: 'user' | 'ai'; text: string; time: string }[];
  
  // Global Search
  isGlobalSearchOpen: boolean;
  globalSearchQuery: string;
  globalSearchResults: any[];

  // System Monitor
  status: SystemStatus;
  
  // Actions
  setAuthenticated: (auth: boolean, token: string | null) => void;
  setSelectedContact: (contact: string | null) => void;
  setSelectedMonth: (month: string | null) => void;
  setActiveTab: (tab: 'chat' | 'analytics') => void;
  setSearchQuery: (query: string) => void;
  setGlobalSearchOpen: (open: boolean) => void;
  setGlobalSearchQuery: (query: string) => void;
  clearRagHistory: () => void;
  setStatus: (status: Partial<SystemStatus>) => void;
  
  // Async operations
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

export const getApiBase = () => {
  if (typeof window === 'undefined') return 'http://127.0.0.1:8000';
  return `http://${window.location.hostname}:8000`;
};

export const getWsUrl = () => {
  if (typeof window === 'undefined') return 'ws://127.0.0.1:8000/ws/status';
  return `ws://${window.location.hostname}:8000/ws/status`;
};

const API_BASE = typeof window === 'undefined' ? 'http://127.0.0.1:8000' : `http://${window.location.hostname}:8000`;


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
    ollama: { model: 'None', online: false }
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

  setSelectedContact: (contact) => {
    set({ 
      selectedContact: contact, 
      selectedMonth: null, 
      availableMonths: [], 
      messages: [], 
      analytics: null, 
      savedProfile: null, 
      profileMeta: null,
      ragChatHistory: []
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
      const res = await fetch(`${API_BASE}/api/contacts`);
      if (res.ok) {
        const data = await res.json();
        set({ contacts: data });
      }
    } catch (e) {
      console.error('Failed to fetch contacts:', e);
    }
  },

  fetchMonths: async (contact) => {
    try {
      const res = await fetch(`${API_BASE}/api/contacts/${contact}/months`);
      if (res.ok) {
        const data = await res.json();
        set({ availableMonths: data });
        // Auto-select latest month by default
        if (data.length > 0) {
          get().setSelectedMonth(data[0]);
        }
      }
    } catch (e) {
      console.error('Failed to fetch months:', e);
    }
  },

  fetchMessages: async (contact, month) => {
    try {
      const res = await fetch(`${API_BASE}/api/contacts/${contact}/messages/${month}`);
      if (res.ok) {
        const data = await res.json();
        set({ messages: data });
      }
    } catch (e) {
      console.error('Failed to fetch messages:', e);
    }
  },

  fetchAnalytics: async (contact) => {
    try {
      const res = await fetch(`${API_BASE}/api/contacts/${contact}/analytics`);
      if (res.ok) {
        const data = await res.json();
        set({ analytics: data });
      }
    } catch (e) {
      console.error('Failed to fetch analytics:', e);
    }
  },

  fetchProfile: async (contact) => {
    try {
      const res = await fetch(`${API_BASE}/api/rag/contacts/${contact}/profile`);
      if (res.ok) {
        const data = await res.json();
        set({ savedProfile: data.profile, profileMeta: data.meta });
      }
    } catch (e) {
      console.error('Failed to fetch profile:', e);
    }
  },

  generateProfile: async (contact, startMonth, endMonth, forceCloud, deepScan, userConsent) => {
    set({ isGeneratingProfile: true });
    try {
      const res = await fetch(`${API_BASE}/api/rag/contacts/${contact}/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_month: startMonth,
          end_month: endMonth,
          force_cloud: forceCloud,
          deep_scan: deepScan,
          user_consent: userConsent
        })
      });
      if (res.ok) {
        const data = await res.json();
        set({ savedProfile: data.profile, profileMeta: data.meta });
      } else {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to generate profile');
      }
    } catch (e) {
      console.error('Failed to generate profile:', e);
      alert(`Error generating personality assessment: ${e.message}`);
    } finally {
      set({ isGeneratingProfile: false });
    }
  },

  queryRAG: async (contact, query, startMonth, endMonth, deepScan, userConsent) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    // Optimistically add user query to history
    set((state) => ({
      isQueryingRAG: true,
      ragChatHistory: [...state.ragChatHistory, { sender: 'user', text: query, time: timeStr }]
    }));
    
    try {
      const res = await fetch(`${API_BASE}/api/rag/contacts/${contact}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          start_month: startMonth,
          end_month: endMonth,
          deep_scan: deepScan,
          user_consent: userConsent
        })
      });
      if (res.ok) {
        const data = await res.json();
        const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        set((state) => ({
          ragChatHistory: [...state.ragChatHistory, { sender: 'ai', text: data.response, time: responseTimeStr }]
        }));
      } else {
        const err = await res.json();
        throw new Error(err.detail || 'Query failed');
      }
    } catch (e) {
      console.error('RAG Query failed:', e);
      const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      set((state) => ({
        ragChatHistory: [...state.ragChatHistory, { sender: 'ai', text: `Error: RAG index query failed. Details: ${e.message}`, time: responseTimeStr }]
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
      const res = await fetch(`${API_BASE}/api/rag/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      if (res.ok) {
        const data = await res.json();
        set({ globalSearchResults: data });
      }
    } catch (e) {
      console.error('Global search failed:', e);
    }
  },

  logoutInstagram: async () => {
    // Session cleanup is handled via the backend when new credentials fail or sessions expire.
    // Here we can simply clear local state or trigger a login reset.
    console.log('Instagram session cleanup triggered');
  },

  triggerInstagramSync: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/instagram/sync/once`, { method: 'POST' });
      return res.ok;
    } catch (e) {
      console.error('Failed to trigger manual sync:', e);
      return false;
    }
  },

  toggleDaemonSync: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/instagram/sync/toggle`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        return data.daemon_sync_active;
      }
      return false;
    } catch (e) {
      console.error('Failed to toggle background sync daemon:', e);
      return false;
    }
  }
}));
