'use client';

import React, { useEffect, useRef } from 'react';
import { useSyncStore } from '../store/useSyncStore';
import { Search, Sparkles, X, Database, Bot } from 'lucide-react';

export default function GlobalSearch() {
  const {
    isGlobalSearchOpen,
    globalSearchQuery,
    globalSearchResults,
    setGlobalSearchOpen,
    setGlobalSearchQuery,
    globalSearch,
    setSelectedContact
  } = useSyncStore();

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
  }, [isGlobalSearchOpen, setGlobalSearchOpen]);

  // Focus input field when modal opens
  useEffect(() => {
    if (isGlobalSearchOpen && inputRef.current) {
      // Small timeout ensures layout and animations have initialized
      const focusTimer = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(focusTimer);
    }
  }, [isGlobalSearchOpen]);

  if (!isGlobalSearchOpen) return null;

  const handleSelectResult = (contactName: string) => {
    setSelectedContact(contactName);
    setGlobalSearchOpen(false);
    setGlobalSearchQuery('');
  };

  return (
    <div 
      className="fixed inset-0 bg-[rgba(3,3,5,0.7)] backdrop-blur-md flex items-start justify-center pt-24 z-50 animate-fade-in font-sans"
      role="dialog"
      aria-modal="true"
      aria-labelledby="global-search-title"
    >
      
      {/* Frosted Command Palette Panel */}
      <div className="w-full max-w-xl glass-panel-heavy p-5 flex flex-col gap-4 max-h-[500px] border border-[var(--border-glass-bright)] shadow-2xl shadow-[rgba(121,99,255,0.12)] relative animate-scale-up">
        
        {/* Close Button */}
        <button 
          onClick={() => setGlobalSearchOpen(false)}
          className="absolute right-4 top-4 text-zinc-500 hover:text-white p-1 hover:bg-[rgba(255,255,255,0.05)] rounded-lg transition-colors cursor-pointer"
          aria-label="Close search"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header */}
        <div id="global-search-title" className="flex items-center gap-2 text-xs font-bold text-primary">
          <Sparkles className="w-4 h-4" /> Global Intelligence Command Palette
        </div>

        {/* Input Bar */}
        <div className="relative shrink-0">
          <Search className="w-4.5 h-4.5 text-zinc-500 absolute left-3 top-3.5" />
          <input
            ref={inputRef}
            type="text"
            value={globalSearchQuery}
            onChange={(e) => {
              setGlobalSearchQuery(e.target.value);
              globalSearch(e.target.value);
            }}
            placeholder="Type semantic query (e.g., project discussions, plans)..."
            className="w-full pl-10 pr-4 py-3 bg-[rgba(255,255,255,0.015)] border border-[var(--border-glass)] rounded-xl text-xs text-white outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all font-sans"
            aria-label="Semantic search query"
          />
        </div>

        {/* Shortcut Info */}
        <div className="text-[10px] text-zinc-500 shrink-0 select-none">
          Press <kbd className="bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800 text-zinc-400">ESC</kbd> to close.
        </div>

        {/* Scrollable Matches List */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-2.5 scrollbar-thin scrollbar-thumb-zinc-800">
          {globalSearchResults.length > 0 ? (
            globalSearchResults.map((match) => (
              <div
                key={match.id}
                onClick={() => handleSelectResult(match.chat_name)}
                className="p-3.5 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg hover:bg-[rgba(121,99,255,0.04)] hover:border-[rgba(121,99,255,0.25)] cursor-pointer transition-all duration-200 group"
              >
                <div className="flex justify-between items-center text-[10px] font-bold mb-2">
                  <div className="flex items-center gap-1.5 text-accent-cyan group-hover:text-primary transition-colors">
                    <Database className="w-3.5 h-3.5" />
                    <span>@{match.chat_name}</span>
                  </div>
                  <span className="text-zinc-500 font-mono">{match.month}</span>
                </div>
                
                <p className="text-[11px] text-zinc-300 leading-relaxed font-sans group-hover:text-white transition-colors">
                  {match.document}
                </p>
                
                <div className="mt-2 text-[8px] text-primary font-bold uppercase opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                  <Bot className="w-3 h-3" /> Jump to conversation history
                </div>
              </div>
            ))
          ) : globalSearchQuery.trim() ? (
            <div className="h-32 flex items-center justify-center text-xs text-zinc-500 italic select-none">
              No matching semantic blocks found.
            </div>
          ) : (
            <div className="h-32 flex flex-col items-center justify-center gap-1.5 text-xs text-zinc-500 select-none">
              <span>Start typing to search across all chats...</span>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
