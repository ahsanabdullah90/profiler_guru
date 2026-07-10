'use client';

import React, { useEffect, useState, memo } from 'react';
import { useContactsStore } from '../store/contactsStore';
import { useTagsStore } from '../store/tagsStore';
import { useNotesStore, type Note } from '../store/notesStore';
import { useFlagsStore } from '../store/flagsStore';
import { useUIStore } from '../store/uiStore';
import { useDebouncedCallback } from '../lib/useDebounce';
import InspectorSection from './ui/InspectorSection';
import {
  X,
  Star,
  Archive,
  Plus,
  StickyNote,
  Trash2,
  ChevronLeft,
  Info,
} from 'lucide-react';

// Stable fallback references for Zustand selectors — prevents infinite
// re-render loops when a contact has no tags/notes/flags yet.
const EMPTY_TAGS: string[] = [];
const EMPTY_NOTES: Note[] = [];
const DEFAULT_FLAGS = { starred: false, archived: false };

export default function Inspector() {
  const selectedContact = useContactsStore((s) => s.selectedContact);
  const contacts = useContactsStore((s) => s.contacts);
  const contactInfo = contacts.find((c) => c.client_id === selectedContact || c.name === selectedContact);
  const displayName = contactInfo?.display_name || selectedContact || '';
  const analytics = useContactsStore((s) => s.analytics);
  const inspectorOpen = useUIStore((s) => s.inspectorOpen);
  const inspectorWidth = useUIStore((s) => s.inspectorWidth);
  const setInspectorWidth = useUIStore((s) => s.setInspectorWidth);
  const toggleInspector = useUIStore((s) => s.toggleInspector);
  const inspectorHintShown = useUIStore((s) => s.inspectorHintShown);
  const dismissInspectorHint = useUIStore((s) => s.dismissInspectorHint);

  const tags = useTagsStore((s) =>
    selectedContact ? s.tagsByContact[selectedContact] ?? EMPTY_TAGS : EMPTY_TAGS,
  );
  const fetchTags = useTagsStore((s) => s.fetchTags);
  const addTag = useTagsStore((s) => s.addTag);
  const removeTag = useTagsStore((s) => s.removeTag);

  const notes = useNotesStore((s) =>
    selectedContact ? s.notesByContact[selectedContact] ?? EMPTY_NOTES : EMPTY_NOTES,
  );
  const fetchNotes = useNotesStore((s) => s.fetchNotes);
  const addNote = useNotesStore((s) => s.addNote);
  const updateNote = useNotesStore((s) => s.updateNote);
  const deleteNote = useNotesStore((s) => s.deleteNote);


  const flags = useFlagsStore((s) =>
    selectedContact ? s.flagsByContact[selectedContact] ?? DEFAULT_FLAGS : DEFAULT_FLAGS,
  );
  const fetchFlags = useFlagsStore((s) => s.fetchFlags);
  const setStarred = useFlagsStore((s) => s.setStarred);
  const setArchived = useFlagsStore((s) => s.setArchived);

  const [tagInput, setTagInput] = useState('');
  const [noteInput, setNoteInput] = useState('');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');
  const [drawerMode, setDrawerMode] = useState(false);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;
    const check = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => setDrawerMode(window.innerWidth < 1440), 150);
    };
    check();
    window.addEventListener('resize', check);
    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener('resize', check);
    };
  }, []);

  useEffect(() => {
    if (selectedContact) {
      fetchTags(selectedContact);
      fetchNotes(selectedContact);
      fetchFlags(selectedContact);
    }
  }, [selectedContact, fetchTags, fetchNotes, fetchFlags]);

  const persistEdit = useDebouncedCallback((id: string, text: string) => {
    if (selectedContact) updateNote(selectedContact, id, text);
  }, 1000);

  if (!inspectorOpen) {
    return (
      <button
        type="button"
        onClick={toggleInspector}
        aria-label="Open inspector"
        className="w-9 h-12 flex items-center justify-center bg-[var(--bg-surface-raised)] border border-[var(--border-subtle)] border-l-0 rounded-r-md text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
        style={{ position: drawerMode ? 'fixed' : 'relative', right: 0, top: '50%', transform: 'translateY(-50%)' }}
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
    );
  }

  const width = drawerMode ? Math.min(360, Math.max(280, window.innerWidth - 40)) : inspectorWidth;

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = inspectorWidth;
    const onMove = (ev: MouseEvent) => {
      const delta = startX - ev.clientX;
      setInspectorWidth(startWidth + delta);
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  return (
    <aside
      className={`bg-[var(--bg-surface-raised)] border-l border-[var(--border-subtle)] flex flex-col overflow-hidden ${
        drawerMode ? 'fixed right-0 top-[56px] bottom-0 z-40 shadow-2xl' : 'relative'
      }`}
      style={{ width: `${width}px` }}
      aria-label="Contact inspector"
    >
      {!drawerMode ? (
        <div
          onMouseDown={handleResizeStart}
          className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-[var(--brand-primary)] transition-colors"
          aria-hidden="true"
        />
      ) : null}

      <div className="px-3 py-2.5 border-b border-[var(--border-subtle)] flex items-center justify-between shrink-0">
        <h2 className="text-[10px] uppercase tracking-wider text-[var(--text-muted)] font-bold">Inspector</h2>
        <button type="button" onClick={toggleInspector} aria-label="Close inspector" className="w-6 h-6 inline-flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {!inspectorHintShown ? (
        <div className="mx-3 mt-2 p-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md flex items-start gap-2 text-[10px] text-[var(--text-secondary)] shrink-0">
          <Info className="w-3 h-3 mt-0.5 shrink-0 text-[var(--brand-primary)]" aria-hidden="true" />
          <span className="flex-1 leading-relaxed">
            This pane shows contact details. Hide with{' '}
            <kbd className="font-mono px-1 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--bg-surface-inset)] text-[9px]">Ctrl+I</kbd>.
          </span>
          <button type="button" onClick={dismissInspectorHint} aria-label="Dismiss inspector hint" className="text-[var(--text-muted)] hover:text-[var(--text-primary)] shrink-0">
            <X className="w-3 h-3" />
          </button>
        </div>
      ) : null}

      <div className="flex-1 overflow-y-auto px-3">
        {!selectedContact ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-[var(--text-muted)] text-xs py-12 gap-2">
            <Info className="w-5 h-5 opacity-50" />
            <p>Select a contact to see details here.</p>
          </div>
        ) : (
          <>
            <InspectorSection title="Overview">
              <div className="space-y-1.5">
                <h3 className="text-sm font-bold text-[var(--text-primary)] truncate">{displayName}</h3>
                {analytics ? (
                  <div className="grid grid-cols-2 gap-2 text-[10px]">
                    <Stat label="Messages" value={analytics.total_messages.toLocaleString()} />
                    <Stat label="Voice" value={`${analytics.audio_ratio}%`} />
                    <Stat label="Weekly Avg" value={analytics.avg_msg_weekly.toFixed(2)} />
                    <Stat label="Monthly Avg" value={analytics.avg_msg_monthly.toFixed(2)} />
                  </div>
                ) : (
                  <p className="text-[10px] text-[var(--text-muted)] italic">Loading analytics…</p>
                )}
              </div>
            </InspectorSection>

            <InspectorSection title="Quick Actions">
              <div className="flex flex-wrap gap-1.5">
                <ActionPill icon={<Star className="w-3 h-3" />} label={flags.starred ? 'Starred' : 'Star'} active={flags.starred} onClick={() => setStarred(selectedContact, !flags.starred)} />
                <ActionPill icon={<Archive className="w-3 h-3" />} label={flags.archived ? 'Archived' : 'Archive'} active={flags.archived} onClick={() => setArchived(selectedContact, !flags.archived)} />
              </div>
            </InspectorSection>

            <InspectorTags
              tags={tags}
              selectedContact={selectedContact}
              addTag={addTag}
              removeTag={removeTag}
              tagInput={tagInput}
              setTagInput={setTagInput}
            />

            <InspectorNotes
              notes={notes}
              selectedContact={selectedContact}
              editingNoteId={editingNoteId}
              setEditingNoteId={setEditingNoteId}
              editingText={editingText}
              setEditingText={setEditingText}
              updateNote={updateNote}
              deleteNote={deleteNote}
              addNote={addNote}
              noteInput={noteInput}
              setNoteInput={setNoteInput}
              persistEdit={persistEdit}
            />
          </>
        )}
      </div>
    </aside>
  );
}

// ──────────────────────────────────────────────────────────────────
// Memoized sub-components — only re-render when their own props change
// ──────────────────────────────────────────────────────────────────

const InspectorTags = memo(function InspectorTags({
  tags,
  selectedContact,
  addTag,
  removeTag,
  tagInput,
  setTagInput,
}: {
  tags: string[];
  selectedContact: string;
  addTag: (contact: string, tag: string) => Promise<void>;
  removeTag: (contact: string, tag: string) => Promise<void>;
  tagInput: string;
  setTagInput: (v: string) => void;
}) {
  return (
    <InspectorSection title="Tags">
      <div className="flex flex-wrap gap-1 mb-2">
        {tags.length === 0 ? (
          <span className="text-[10px] text-[var(--text-muted)] italic">No tags yet</span>
        ) : (
          tags.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => removeTag(selectedContact, tag)}
              className="h-6 px-2 inline-flex items-center gap-1 text-[10px] font-semibold rounded-full border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-primary)] hover:border-[var(--brand-primary)] hover:text-[var(--brand-primary)] transition-colors"
              title={`Remove tag "${tag}"`}
            >
              {tag}
              <X className="w-2.5 h-2.5 opacity-60" />
            </button>
          ))
        )}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (tagInput.trim()) {
            addTag(selectedContact, tagInput.trim());
            setTagInput('');
          }
        }}
        className="flex gap-1"
      >
        <input
          type="text"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          placeholder="Add tag…"
          aria-label="New tag"
          maxLength={64}
          className="flex-1 h-7 px-2 text-[11px] bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--brand-primary)]"
        />
        <button
          type="submit"
          disabled={!tagInput.trim()}
          className="h-7 w-7 inline-flex items-center justify-center bg-[var(--brand-primary)] text-white rounded disabled:opacity-40 hover:bg-[var(--brand-primary-strong)] transition-colors"
          aria-label="Add tag"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </form>
    </InspectorSection>
  );
});

const InspectorNotes = memo(function InspectorNotes({
  notes,
  selectedContact,
  editingNoteId,
  setEditingNoteId,
  editingText,
  setEditingText,
  updateNote,
  deleteNote,
  addNote,
  noteInput,
  setNoteInput,
  persistEdit,
}: {
  notes: { id: string; note: string; session_date?: string | null; note_type?: string; consent_version?: string | null; created_at: string; updated_at: string }[];
  selectedContact: string;
  editingNoteId: string | null;
  setEditingNoteId: (id: string | null) => void;
  editingText: string;
  setEditingText: (v: string) => void;
  updateNote: (contact: string, id: string, text: string) => Promise<void>;
  deleteNote: (contact: string, id: string) => Promise<void>;
  addNote: (contact: string, text: string, sessionDate?: string, noteType?: string) => Promise<Note | null>;
  noteInput: string;
  setNoteInput: (v: string) => void;
  persistEdit: (id: string, text: string) => void;
}) {
  const [newNoteType, setNewNoteType] = useState('free');
  const [newNoteDate, setNewNoteDate] = useState(new Date().toISOString().slice(0, 10));
  return (
    <InspectorSection title={`Notes (${notes.length})`}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (noteInput.trim()) {
            await addNote(selectedContact, noteInput.trim(), newNoteDate, newNoteType);
            setNoteInput('');
          }
        }}
        className="mb-3"
      >
        <textarea
          value={noteInput}
          onChange={(e) => setNoteInput(e.target.value)}
          placeholder="Add a clinical observation…"
          aria-label="New note"
          rows={2}
          maxLength={10000}
          className="w-full px-2 py-1.5 text-[11px] bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--brand-primary)] resize-none"
        />
        <div className="flex items-center gap-2 mt-1.5">
          <select
            value={newNoteType}
            onChange={(e) => setNewNoteType(e.target.value)}
            className="px-1.5 py-1 text-[9px] bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded text-[var(--text-secondary)] outline-none"
          >
            <option value="free">Free-form</option>
            <option value="soap">SOAP</option>
            <option value="dap">DAP</option>
            <option value="progress">Progress</option>
          </select>
          <input
            type="date"
            value={newNoteDate}
            onChange={(e) => setNewNoteDate(e.target.value)}
            className="px-1.5 py-1 text-[9px] bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded text-[var(--text-secondary)] outline-none"
          />
          <div className="flex-1" />
          <button
            type="submit"
            disabled={!noteInput.trim()}
            className="h-7 px-2.5 inline-flex items-center gap-1 text-[10px] font-bold bg-[var(--brand-primary)] text-white rounded disabled:opacity-40 hover:bg-[var(--brand-primary-strong)] transition-colors"
          >
            <StickyNote className="w-3 h-3" /> Save Note
          </button>
        </div>
      </form>
      <ul className="space-y-1.5">
        {notes.length === 0 ? (
          <li className="text-[10px] text-[var(--text-muted)] italic">No notes yet</li>
        ) : (
          notes.map((n) => (
            <li key={n.id} className="p-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded group">
              <div className="flex items-center gap-1.5 mb-1">
                {n.note_type && n.note_type !== 'free' ? (
                  <span className="px-1 py-0.5 rounded text-[8px] font-bold uppercase"
                    style={{
                      background: n.note_type === 'soap' ? 'rgba(59, 130, 246, 0.1)' :
                                 n.note_type === 'dap' ? 'rgba(16, 185, 129, 0.1)' :
                                 'rgba(245, 158, 11, 0.1)',
                      color: n.note_type === 'soap' ? '#3B82F6' :
                             n.note_type === 'dap' ? '#10B981' :
                             '#F59E0B',
                    }}
                  >
                    {n.note_type.toUpperCase()}
                  </span>
                ) : null}
                {n.session_date ? (
                  <span className="text-[8px] font-mono text-[var(--text-muted)]">{n.session_date}</span>
                ) : null}
              </div>
              {editingNoteId === n.id ? (
                <textarea
                  value={editingText}
                  onChange={(e) => {
                    setEditingText(e.target.value);
                    persistEdit(n.id, e.target.value);
                  }}
                  onBlur={() => {
                    if (selectedContact) updateNote(selectedContact, n.id, editingText);
                    setEditingNoteId(null);
                  }}
                  // eslint-disable-next-line jsx-a11y/no-autofocus -- user clicked to edit, focus is the expected action
                  autoFocus
                  rows={3}
                  className="w-full text-[11px] bg-transparent text-[var(--text-primary)] outline-none resize-none"
                />
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    setEditingNoteId(n.id);
                    setEditingText(n.note);
                  }}
                  className="block w-full text-left text-[11px] text-[var(--text-primary)] whitespace-pre-wrap cursor-text leading-relaxed bg-transparent border-0 p-0"
                >
                  {n.note}
                </button>
              )}
              <div className="flex items-center justify-between mt-1.5 text-[9px] text-[var(--text-muted)]">
                <span className="font-mono">{new Date(n.updated_at).toLocaleString()}</span>
                <button
                  type="button"
                  onClick={() => {
                    if (confirm('Delete this note?')) deleteNote(selectedContact, n.id);
                  }}
                  aria-label="Delete note"
                  className="text-[var(--text-muted)] hover:text-[var(--error)] transition-colors"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </li>
          ))
        )}
      </ul>
    </InspectorSection>
  );
});

// ──────────────────────────────────────────────────────────────────
// Small presentational components (no state, no memo needed)
// ──────────────────────────────────────────────────────────────────

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-1.5 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded">
      <div className="text-[9px] uppercase text-[var(--text-muted)] tracking-wider">{label}</div>
      <div className="text-[11px] font-mono font-bold text-[var(--text-primary)] mt-0.5">{value}</div>
    </div>
  );
}

function ActionPill({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-bold rounded-md border transition-colors ${
        active
          ? 'bg-[var(--brand-primary-soft)] border-[var(--brand-primary)] text-[var(--brand-primary)]'
          : 'bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
