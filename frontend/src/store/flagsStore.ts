'use client';

import { create } from 'zustand';
import { apiFetch } from './api';

interface FlagsState {
  flagsByContact: Record<string, { starred: boolean; archived: boolean }>;

  fetchFlags: (contact: string) => Promise<void>;
  setStarred: (contact: string, starred: boolean) => Promise<void>;
  setArchived: (contact: string, archived: boolean) => Promise<void>;
}

const DEFAULT_FLAGS = { starred: false, archived: false };

export const useFlagsStore = create<FlagsState>((set) => ({
  flagsByContact: {},

  fetchFlags: async (contact) => {
    try {
      const res = await apiFetch<{ contact: string; starred: boolean; archived: boolean }>(
        `/inspector/${encodeURIComponent(contact)}/flags`,
      );
      set((s) => ({
        flagsByContact: {
          ...s.flagsByContact,
          [contact]: { starred: res.starred, archived: res.archived },
        },
      }));
    } catch {
      // Silent failure — Inspector shows default flags if fetch fails.
    }
  },

  setStarred: async (contact, starred) => {
    set((s) => {
      const before = s.flagsByContact[contact] ?? DEFAULT_FLAGS;
      const optimistic = { ...before, starred };
      return { flagsByContact: { ...s.flagsByContact, [contact]: optimistic } };
    });
    try {
      const res = await apiFetch<{ contact: string; starred: boolean; archived: boolean }>(
        `/inspector/${encodeURIComponent(contact)}/flags`,
        { method: 'PATCH', body: JSON.stringify({ starred }) },
      );
      set((s) => ({
        flagsByContact: {
          ...s.flagsByContact,
          [contact]: { starred: res.starred, archived: res.archived },
        },
      }));
    } catch {
      // Revert to whatever the server last returned (next fetch will resync).
    }
  },

  setArchived: async (contact, archived) => {
    set((s) => {
      const before = s.flagsByContact[contact] ?? DEFAULT_FLAGS;
      const optimistic = { ...before, archived };
      return { flagsByContact: { ...s.flagsByContact, [contact]: optimistic } };
    });
    try {
      const res = await apiFetch<{ contact: string; starred: boolean; archived: boolean }>(
        `/inspector/${encodeURIComponent(contact)}/flags`,
        { method: 'PATCH', body: JSON.stringify({ archived }) },
      );
      set((s) => ({
        flagsByContact: {
          ...s.flagsByContact,
          [contact]: { starred: res.starred, archived: res.archived },
        },
      }));
    } catch {
      // Revert to whatever the server last returned (next fetch will resync).
    }
  },
}));
