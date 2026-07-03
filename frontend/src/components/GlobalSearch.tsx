'use client';

import React, { useEffect, useRef } from 'react';
import { useRagStore } from '../store/ragStore';
import { useContactsStore } from '../store/contactsStore';
import { useDebouncedCallback } from '../lib/useDebounce';
import { Search, Sparkles, X, Database, Bot, Inbox } from 'lucide-react';
import EmptyState from './ui/EmptyState';

export default function GlobalSearch() {
  const isGlobalSearchOpen = useRagStore((s) => s.isGlobalSearchOpen);
  const globalSearchQuery = useRagStore((s) => s.globalSearchQuery);
  const globalSearchResults = useRagStore((s) => s.globalSearchResults);
  const setGlobalSearchOpen = useRagStore((s) => s.setGlobalSearchOpen);
  const setGlobalSearchQuery = useRagStore((s) => s.setGlobalSearchQuery);
  const globalSearch = useRagStore((s) => s.globalSearch);
  const setSelectedContact = useContactsStore((s) => s.setSelectedContact);

  const inputRef = useRef<HTMLInputElement>(null);

  // Toggle overlay on Ctrl+K shortcut keys
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setGlobalSearchOpen(!isGlobalSearchOpen);
      }
      if (e.key === 'Escape' && isGlobalSearchOpen) {
        setGlobalSearchOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setGlobalSearchOpen, isGlobalSearchOpen]);

  // Focus input field when modal opens
  useEffect(() => {
    if (isGlobalSearchOpen && inputRef.current) {
      const focusTimer = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(focusTimer);
    }
  }, [isGlobalSearchOpen]);

  const handleSearch = useDebouncedCallback((value: string) => {
    setGlobalSearchQuery(value);
    globalSearch(value);
  }, 300);

  if (!isGlobalSearchOpen) return null;

  const handleSelectResult = (contactName: string) => {
    setSelectedContact(contactName);
    setGlobalSearchOpen(false);
    setGlobalSearchQuery('');
  };

  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- modal dialog backdrop with explicit Escape/Enter/Space handling
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 font-sans"
      style={{ background: 'rgba(11, 11, 14, 0.78)', backdropFilter: 'blur(8px)' }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="global-search-title"
      tabIndex={-1}
      onClick={(e) => {
        // Close on backdrop click
        if (e.target === e.currentTarget) setGlobalSearchOpen(false);
      }}
      onKeyDown={(e) => {
        // Close on Enter/Space when the backdrop has focus
        if ((e.key === 'Enter' || e.key === ' ') && e.target === e.currentTarget) {
          setGlobalSearchOpen(false);
        }
      }}
    >
      {/* Frosted Command Palette Panel */}
      <div
        className="w-full max-w-xl flex flex-col gap-4 max-h-[500px] border rounded-xl shadow-2xl relative p-5"
        style={{
          background: 'var(--bg-surface-raised)',
          borderColor: 'var(--border-subtle)',
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.6), 0 0 24px var(--brand-primary-glow)',
        }}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={() => setGlobalSearchOpen(false)}
          className="absolute right-3 top-3 p-1 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
          aria-label="Close search"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header */}
        <div
          id="global-search-title"
          className="flex items-center gap-2 text-xs font-bold"
          style={{ color: 'var(--brand-primary)' }}
        >
          <Sparkles className="w-4 h-4" />
          Global Intelligence Command Palette
        </div>

        {/* Input Bar */}
        <div className="relative shrink-0">
          <Search
            className="w-5 h-5 absolute left-3 top-3.5"
            style={{ color: 'var(--text-muted)' }}
            aria-hidden="true"
          />
          <input
            ref={inputRef}
            type="text"
            value={globalSearchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Type semantic query (e.g., project discussions, plans)..."
            className="w-full pl-10 pr-4 py-3 rounded-xl text-xs text-[var(--text-primary)] outline-none transition-all"
            style={{
              background: 'var(--bg-surface-inset)',
              border: '1px solid var(--border-subtle)',
            }}
            aria-label="Semantic search query"
          />
        </div>

        {/* Shortcut Info */}
        <div
          className="text-[10px] shrink-0 select-none flex items-center gap-2"
          style={{ color: 'var(--text-muted)' }}
        >
          <span>
            Press{' '}
            <kbd
              className="px-1.5 py-0.5 rounded border font-mono"
              style={{
                background: 'var(--bg-surface-inset)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-secondary)',
              }}
            >
              ESC
            </kbd>{' '}
            to close
          </span>
          <span aria-hidden="true">·</span>
          <span>
            <kbd
              className="px-1.5 py-0.5 rounded border font-mono"
              style={{
                background: 'var(--bg-surface-inset)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-secondary)',
              }}
            >
              ↵
            </kbd>{' '}
            to open result
          </span>
        </div>

        {/* Scrollable Matches List */}
        <div
          className="flex-1 overflow-y-auto pr-1 space-y-2.5"
          style={{ scrollbarWidth: 'thin' }}
        >
          {globalSearchResults.length > 0 ? (
            globalSearchResults.map((match) => (
              <button
                key={match.id}
                type="button"
                onClick={() => handleSelectResult(match.chat_name)}
                className="p-3 rounded-lg border text-left w-full transition-all duration-200 group focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
                style={{
                  background: 'var(--bg-surface)',
                  borderColor: 'var(--border-subtle)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--brand-primary-soft)';
                  e.currentTarget.style.borderColor = 'var(--brand-primary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'var(--bg-surface)';
                  e.currentTarget.style.borderColor = 'var(--border-subtle)';
                }}
              >
                <div className="flex justify-between items-center text-[10px] font-bold mb-2">
                  <div
                    className="flex items-center gap-1.5 transition-colors"
                    style={{ color: 'var(--data-1)' }}
                  >
                    <Database className="w-3.5 h-3.5" />
                    <span>@{match.chat_name}</span>
                  </div>
                  <span
                    className="font-mono"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {match.month}
                  </span>
                </div>
                <p
                  className="text-[11px] leading-relaxed transition-colors"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {match.document}
                </p>
                <div
                  className="mt-2 text-[8px] font-bold uppercase opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1"
                  style={{ color: 'var(--brand-primary)' }}
                >
                  <Bot className="w-3 h-3" /> Jump to conversation history
                </div>
              </button>
            ))
          ) : globalSearchQuery.trim() ? (
            <div
              className="h-32 flex items-center justify-center text-xs italic select-none"
              style={{ color: 'var(--text-muted)' }}
            >
              <Inbox
                className="w-4 h-4 mr-2 opacity-60"
                style={{ color: 'var(--text-muted)' }}
                aria-hidden="true"
              />
              No matching semantic blocks found.
            </div>
          ) : (
            <EmptyState
              icon={<Search className="w-5 h-5" />}
              title="Start typing to search"
              description="Searches across all indexed chats and transcription logs using semantic embeddings."
              className="min-h-[160px]"
            />
          )}
        </div>
      </div>
    </div>
  );
}
