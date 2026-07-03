'use client';

import { create } from 'zustand';
import { apiFetch } from './api';

export interface Note {
  id: string;
  note: string;
  created_at: string;
  updated_at: string;
}

interface NotesState {
  notesByContact: Record<string, Note[]>;

  fetchNotes: (contact: string) => Promise<void>;
  addNote: (contact: string, text: string) => Promise<Note | null>;
  updateNote: (contact: string, id: string, text: string) => Promise<void>;
  deleteNote: (contact: string, id: string) => Promise<void>;
}

export const useNotesStore = create<NotesState>((set) => ({
  notesByContact: {},

  fetchNotes: async (contact) => {
    try {
      const res = await apiFetch<{ contact: string; notes: Note[] }>(
        `/inspector/${encodeURIComponent(contact)}/notes`,
      );
      set((s) => ({
        notesByContact: { ...s.notesByContact, [contact]: res.notes },
      }));
    } catch {
      // Silent failure — Inspector shows empty notes if fetch fails.
    }
  },

  addNote: async (contact, text) => {
    try {
      const note = await apiFetch<Note>(
        `/inspector/${encodeURIComponent(contact)}/notes`,
        { method: 'POST', body: JSON.stringify({ note: text }) },
      );
      set((s) => ({
        notesByContact: {
          ...s.notesByContact,
          [contact]: [note, ...(s.notesByContact[contact] ?? [])],
        },
      }));
      return note;
    } catch {
      return null;
    }
  },

  updateNote: async (contact, id, text) => {
    set((s) => {
      const before = s.notesByContact[contact] ?? [];
      const optimistic = before.map((n) =>
        n.id === id ? { ...n, note: text, updated_at: new Date().toISOString() } : n,
      );
      return { notesByContact: { ...s.notesByContact, [contact]: optimistic } };
    });
    try {
      const note = await apiFetch<Note>(
        `/inspector/${encodeURIComponent(contact)}/notes/${encodeURIComponent(id)}`,
        { method: 'PUT', body: JSON.stringify({ note: text }) },
      );
      set((s) => ({
        notesByContact: {
          ...s.notesByContact,
          [contact]: (s.notesByContact[contact] ?? []).map((n) => (n.id === id ? note : n)),
        },
      }));
    } catch {
      // Revert to whatever the server last returned (next fetch will resync).
    }
  },

  deleteNote: async (contact, id) => {
    set((s) => {
      const before = s.notesByContact[contact] ?? [];
      const optimistic = before.filter((n) => n.id !== id);
      return { notesByContact: { ...s.notesByContact, [contact]: optimistic } };
    });
    try {
      await apiFetch<{ deleted: boolean; note_id: string }>(
        `/inspector/${encodeURIComponent(contact)}/notes/${encodeURIComponent(id)}`,
        { method: 'DELETE' },
      );
    } catch {
      // Revert to whatever the server last returned (next fetch will resync).
    }
  },
}));
