'use client';

import { create } from 'zustand';
import { apiFetch } from './api';

export interface Note {
  id: string;
  note: string;
  session_date?: string | null;
  note_type?: string;
  consent_version?: string | null;
  created_at: string;
  updated_at: string;
}

interface NotesState {
  notesByContact: Record<string, Note[]>;

  fetchNotes: (contact: string) => Promise<void>;
  addNote: (contact: string, text: string, sessionDate?: string, noteType?: string, consentVersion?: string) => Promise<Note | null>;
  updateNote: (contact: string, id: string, text: string, sessionDate?: string, noteType?: string) => Promise<void>;
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

  addNote: async (contact, text, sessionDate?, noteType?, consentVersion?) => {
    try {
      const body: Record<string, unknown> = { note: text };
      if (sessionDate) body.session_date = sessionDate;
      if (noteType) body.note_type = noteType;
      if (consentVersion) body.consent_version = consentVersion;
      const note = await apiFetch<Note>(
        `/inspector/${encodeURIComponent(contact)}/notes`,
        { method: 'POST', body: JSON.stringify(body) },
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

  updateNote: async (contact, id, text, sessionDate?, noteType?) => {
    set((s) => {
      const before = s.notesByContact[contact] ?? [];
      const optimistic = before.map((n) =>
        n.id === id ? { ...n, note: text, updated_at: new Date().toISOString() } : n,
      );
      return { notesByContact: { ...s.notesByContact, [contact]: optimistic } };
    });
    try {
      const body: Record<string, unknown> = { note: text };
      if (sessionDate) body.session_date = sessionDate;
      if (noteType) body.note_type = noteType;
      const note = await apiFetch<Note>(
        `/inspector/${encodeURIComponent(contact)}/notes/${encodeURIComponent(id)}`,
        { method: 'PUT', body: JSON.stringify(body) },
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
