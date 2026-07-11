'use client';

import React, { useRef, useEffect, memo } from 'react';
import {
  Send, RefreshCw, MessageSquare, Bot, User, Search,
} from 'lucide-react';
import type { RagChatError } from '../store/api';
import { useContactsStore } from '../store/contactsStore';

interface ChatMessage {
  time: string;
  sender: string;
  text: string;
  error?: RagChatError;
  sources?: string[];
}

interface Props {
  selectedContact: string;
  ragChatHistory: ChatMessage[];
  isQueryingRAG: boolean;
  ragQuery: string;
  setRagQuery: (value: string) => void;
  handleRAGQuerySubmit: (e: React.FormEvent) => void;
  onRetryError: (err: RagChatError) => void;
  deepScan?: boolean;
  onDeepScanChange?: (v: boolean) => void;
}

function RAGChatPanel({
  selectedContact,
  ragChatHistory,
  isQueryingRAG,
  ragQuery,
  setRagQuery,
  handleRAGQuerySubmit,
  onRetryError,
  deepScan,
  onDeepScanChange,
}: Props) {
  const threadEndRef = useRef<HTMLDivElement>(null);
  const contacts = useContactsStore((s) => s.contacts);
  const contactInfo = contacts.find((c) => c.client_id === selectedContact || c.name === selectedContact);
  const displayName = contactInfo?.display_name || contactInfo?.name || selectedContact;

  useEffect(() => {
    if (threadEndRef.current) {
      threadEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [ragChatHistory]);

  return (
    <div
      className="h-[35%] flex flex-col overflow-hidden relative"
      style={{ background: 'var(--bg-surface)' }}
    >
      {/* Conversation list */}
      <div
        className="flex-1 overflow-y-auto p-4 space-y-3"
        style={{ scrollbarWidth: 'thin' }}
      >
        {ragChatHistory.length > 0 ? (
          ragChatHistory.map((msg, idx) => (
            <div
              key={msg.time + msg.sender + idx}
              className={`flex flex-col max-w-[85%] ${
                msg.sender === 'user' ? 'ml-auto items-end' : 'mr-auto items-start'
              }`}
            >
              <div
                className={`p-2.5 rounded-lg border flex flex-col text-xs leading-normal font-sans shadow-md ${
                  msg.sender === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'
                }`}
                style={
                  msg.sender === 'user'
                    ? {
                        background: 'var(--brand-primary-soft)',
                        borderColor: 'var(--brand-primary)',
                      }
                    : {
                        background: 'var(--bg-surface-raised)',
                        borderColor: 'var(--border-subtle)',
                      }
                }
              >
                <div className="flex items-center gap-4 justify-between mb-1">
                  <strong
                    className="text-[9px] font-bold uppercase flex items-center gap-1"
                    style={{ color: 'var(--brand-primary)' }}
                  >
                    {msg.sender === 'user' ? (
                      <User className="w-3 h-3" />
                    ) : (
                      <Bot className="w-3 h-3" />
                    )}
                    {msg.sender === 'user' ? 'Me (User)' : 'RAG Agent'}
                  </strong>
                  <span
                    className="text-[8px] font-mono"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {msg.time}
                  </span>
                </div>
                {(() => {
                  const err = msg.error;
                  if (err) {
                    return (
                      <div
                        className="flex flex-col gap-2 mt-1 p-2.5 rounded-lg text-[11px]"
                        style={{
                          background: 'rgba(255, 90, 95, 0.05)',
                          border: '1px solid var(--error)',
                          color: 'var(--text-primary)',
                        }}
                      >
                        <span className="font-bold" style={{ color: 'var(--error)' }}>
                          Query Failed
                        </span>
                        <p
                          className="text-[10px] leading-relaxed"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          {err.message}
                        </p>
                        {err.can_retry ? (
                          <button
                            type="button"
                            onClick={() => onRetryError(err)}
                            className="mt-1.5 px-2.5 py-1 text-white text-[9px] font-bold rounded flex items-center gap-1 cursor-pointer self-start shadow-sm"
                            style={{ background: 'var(--error)' }}
                          >
                            <RefreshCw className="w-2.5 h-2.5" />
                            Retry Query
                          </button>
                        ) : null}
                      </div>
                    );
                  }
                  return (
                    <div className="flex flex-col gap-2">
                      <div className="whitespace-pre-wrap text-[var(--text-primary)]">
                        {msg.text}
                      </div>
                      {msg.sources && msg.sources.length > 0 ? (
                        <div className="mt-1.5 pt-1.5 border-t border-[var(--border-subtle)] flex flex-wrap gap-1 items-center">
                          <span className="text-[8px] font-bold uppercase mr-1" style={{ color: 'var(--text-muted)' }}>
                            Sources:
                          </span>
                          {msg.sources.map((src, sIdx) => (
                            <span
                              key={sIdx}
                              className="text-[8px] font-medium px-1.5 py-0.5 rounded border select-none"
                              style={{
                                background: 'var(--bg-surface-raised)',
                                borderColor: 'var(--border-subtle)',
                                color: 'var(--text-secondary)',
                              }}
                            >
                              {src}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })()}
              </div>
            </div>
          ))
        ) : (
          <div
            className="h-full flex items-center justify-center text-[11px] italic text-center gap-1.5 select-none"
            style={{ color: 'var(--text-muted)' }}
          >
            <MessageSquare className="w-4 h-4" style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
            Ask AI anything about DMs history. Response history shows here.
          </div>
        )}
        {isQueryingRAG ? (
          <div
            className="mr-auto flex items-center gap-2 p-2 rounded-lg text-xs"
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
          >
            <RefreshCw className="w-3 h-3 animate-spin" style={{ color: 'var(--brand-primary)' }} />
            <span>Searching vector index…</span>
          </div>
        ) : null}
        <div ref={threadEndRef} />
      </div>

      {/* Input field */}
      <form
        onSubmit={handleRAGQuerySubmit}
        className="p-3 shrink-0 flex flex-col gap-2"
        style={{ borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-surface-raised)' }}
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={ragQuery}
            onChange={(e) => setRagQuery(e.target.value)}
            disabled={isQueryingRAG}
            placeholder={`Ask AI anything about @${displayName}'s DMs logs...`}
            className="flex-1 px-4 py-2 rounded-lg text-xs outline-none focus:border-[var(--brand-primary)] transition-colors disabled:opacity-50"
            style={{ background: 'var(--bg-surface-inset)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
            aria-label="Ask AI a question about this contact's DMs"
          />
          <button
            type="submit"
            disabled={isQueryingRAG || !ragQuery.trim()}
            className="px-4 py-2 text-white font-bold text-xs rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-30"
            style={{ background: 'var(--brand-primary)' }}
          >
            <Send className="w-3.5 h-3.5" /> Send
          </button>
        </div>
        <div className="flex items-center gap-2 text-[10px]">
          <Search className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
          <span style={{ color: 'var(--text-secondary)' }}>Skip vector search (deep scan)</span>
          <input
            type="checkbox"
            checked={deepScan ?? false}
            onChange={(e) => onDeepScanChange?.(e.target.checked)}
            style={{ accentColor: 'var(--brand-primary)' }}
            aria-label="Skip vector search (deep scan)"
          />
        </div>
      </form>
    </div>
  );
}

export default memo(RAGChatPanel);
