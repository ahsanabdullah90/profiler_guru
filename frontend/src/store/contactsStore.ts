import { create } from 'zustand';
import { apiFetch, type Contact, type Message, type Analytics, type SystemStatus } from './api';
import { useStatusStore } from './statusStore';
import { useRagStore } from './ragStore';

interface ContactsState {
  contacts: Contact[];
  selectedContact: string | null;
  selectedMonth: string | null;
  availableMonths: string[];
  messages: Message[];
  analytics: Analytics | null;
  activeTab: 'chat' | 'analytics';
  searchQuery: string;
  contactTotal: number;
  contactPage: number;
  contactPages: number;
  messageTotal: number;
  messagePage: number;
  messagePages: number;
  activeContactController: AbortController | null;

  setSelectedContact: (contact: string | null) => void;
  setSelectedMonth: (month: string | null) => void;
  setActiveTab: (tab: 'chat' | 'analytics') => void;
  setSearchQuery: (query: string) => void;
  fetchContacts: (opts?: { page?: number; limit?: number; search?: string }) => Promise<void>;
  fetchMonths: (contact: string) => Promise<void>;
  fetchMessages: (contact: string, month: string, opts?: { page?: number; limit?: number }) => Promise<void>;
  fetchAnalytics: (contact: string) => Promise<void>;
}

export const useContactsStore = create<ContactsState>((set, get) => ({
  contacts: [],
  selectedContact: null,
  selectedMonth: null,
  availableMonths: [],
  messages: [],
  analytics: null,
  activeTab: 'chat',
  searchQuery: '',
  contactTotal: 0,
  contactPage: 1,
  contactPages: 1,
  messageTotal: 0,
  messagePage: 1,
  messagePages: 1,
  activeContactController: null,

  setSelectedContact: (contact) => {
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
      activeContactController: newController,
    });
    if (contact) {
      get().fetchMonths(contact);
      get().fetchAnalytics(contact);
      useRagStore.getState().fetchProfile(contact);
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

  fetchContacts: async (opts) => {
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
      useStatusStore.getState().pushError(`Failed to load contacts: ${e.message}`, 'error');
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
      useStatusStore.getState().pushError(`Failed to load months for ${contact}: ${e.message}`, 'error');
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
      useStatusStore.getState().pushError(`Failed to load messages: ${e.message}`, 'error');
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
      useStatusStore.getState().pushError(`Failed to load analytics for ${contact}: ${e.message}`, 'error');
    }
  },
}));
