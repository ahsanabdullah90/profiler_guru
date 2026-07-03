'use client';

import { create } from 'zustand';
import { apiFetch } from './api';

interface TagsState {
  tagsByContact: Record<string, string[]>;

  fetchTags: (contact: string) => Promise<void>;
  addTag: (contact: string, tag: string) => Promise<void>;
  removeTag: (contact: string, tag: string) => Promise<void>;
}

export const useTagsStore = create<TagsState>((set) => ({
  tagsByContact: {},

  fetchTags: async (contact) => {
    try {
      const res = await apiFetch<{ contact: string; tags: string[] }>(
        `/inspector/${encodeURIComponent(contact)}/tags`,
      );
      set((s) => ({
        tagsByContact: { ...s.tagsByContact, [contact]: res.tags },
      }));
    } catch {
      // Silent failure — Inspector shows empty tags if fetch fails.
    }
  },

  addTag: async (contact, tag) => {
    set((s) => {
      const before = s.tagsByContact[contact] ?? [];
      const optimistic = Array.from(new Set([...before, tag.trim().toLowerCase()])).sort();
      return { tagsByContact: { ...s.tagsByContact, [contact]: optimistic } };
    });
    try {
      const res = await apiFetch<{ contact: string; tags: string[] }>(
        `/inspector/${encodeURIComponent(contact)}/tags`,
        { method: 'POST', body: JSON.stringify({ tag }) },
      );
      set((s) => ({ tagsByContact: { ...s.tagsByContact, [contact]: res.tags } }));
    } catch {
      // Revert to whatever the server last returned (next fetch will resync).
    }
  },

  removeTag: async (contact, tag) => {
    set((s) => {
      const before = s.tagsByContact[contact] ?? [];
      const optimistic = before.filter((t) => t !== tag);
      return { tagsByContact: { ...s.tagsByContact, [contact]: optimistic } };
    });
    try {
      const res = await apiFetch<{ contact: string; tags: string[] }>(
        `/inspector/${encodeURIComponent(contact)}/tags/${encodeURIComponent(tag)}`,
        { method: 'DELETE' },
      );
      set((s) => ({ tagsByContact: { ...s.tagsByContact, [contact]: res.tags } }));
    } catch {
      // Revert to whatever the server last returned (next fetch will resync).
    }
  },
}));
