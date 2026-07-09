'use client';

import React, { useEffect, useState } from 'react';
import { apiFetch } from '../store/api';
import { GitMerge, X, Loader2 } from 'lucide-react';

interface PendingMerge {
  suggestion_id: number;
  new_chat_name: string;
  existing_chat_name: string;
  reason: string;
  similarity: number | null;
  created_at: string;
}

export default function MergeSuggestionBanner({ onMerged }: { onMerged: () => void }) {
  const [suggestions, setSuggestions] = useState<PendingMerge[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState<number | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await apiFetch<{ pending_merges: PendingMerge[] }>('/contacts/pending-merges');
        setSuggestions(data.pending_merges || []);
      } catch {
        // Ignore
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading || suggestions.length === 0) return null;

  const handleDismiss = async (id: number) => {
    setActionId(id);
    try {
      await apiFetch('/contacts/pending-merges/dismiss', {
        method: 'POST',
        body: JSON.stringify({ suggestion_id: id }),
      });
      setSuggestions((prev) => prev.filter((s) => s.suggestion_id !== id));
    } catch {
      // Ignore
    } finally {
      setActionId(null);
    }
  };

  const handleConfirm = async (s: PendingMerge) => {
    setActionId(s.suggestion_id);
    try {
      await apiFetch('/contacts/pending-merges/confirm', {
        method: 'POST',
        body: JSON.stringify({ suggestion_id: s.suggestion_id }),
      });
      setSuggestions((prev) => prev.filter((p) => p.suggestion_id !== s.suggestion_id));
      onMerged();
    } catch {
      // Ignore
    } finally {
      setActionId(null);
    }
  };

  return (
    <div className="mb-3 space-y-2">
      {suggestions.map((s) => (
        <div
          key={s.suggestion_id}
          className="flex items-center justify-between p-3 rounded-lg border border-amber-400/20"
          style={{ background: 'rgba(251, 191, 36, 0.06)' }}
        >
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <GitMerge className="w-4 h-4 text-amber-400 shrink-0" />
            <div className="min-w-0">
              <p className="text-[11px] font-semibold text-[var(--text-primary)] truncate">
                &ldquo;{s.new_chat_name}&rdquo; might be the same as &ldquo;{s.existing_chat_name}&rdquo;
              </p>
              <p className="text-[9px] text-[var(--text-muted)] truncate">{s.reason}</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 shrink-0 ml-3">
            <button
              onClick={() => handleConfirm(s)}
              disabled={actionId === s.suggestion_id}
              className="px-2.5 py-1 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors disabled:opacity-50 flex items-center gap-1"
            >
              {actionId === s.suggestion_id ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : null}
              Merge
            </button>
            <button
              onClick={() => handleDismiss(s.suggestion_id)}
              disabled={actionId === s.suggestion_id}
              className="px-2 py-1 rounded text-[9px] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-colors disabled:opacity-50"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
