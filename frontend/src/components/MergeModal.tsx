'use client';

import React, { useState, useMemo } from 'react';
import { apiFetch, type Contact } from '../store/api';
import { X, Search, AlertTriangle, Loader2, ArrowRight } from 'lucide-react';
import PlatformBadge from './PlatformBadge';

interface Props {
  primary: Contact;
  allContacts: Contact[];
  onClose: () => void;
  onMerged: () => void;
}

export default function MergeModal({ primary, allContacts, onClose, onMerged }: Props) {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Contact | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const candidates = useMemo(() => {
    if (!search.trim()) return [];
    const q = search.toLowerCase();
    return allContacts.filter(
      (c) => c.name !== primary.name && c.name.toLowerCase().includes(q),
    ).slice(0, 10);
  }, [search, allContacts, primary.name]);

  const handleMerge = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      const res = await apiFetch<Record<string, number>>('/contacts/merge', {
        method: 'POST',
        body: JSON.stringify({
          primary_chat_name: primary.name,
          secondary_chat_name: selected.name,
        }),
      });
      const summary = Object.entries(res)
        .filter(([, v]) => v > 0)
        .map(([k, v]) => `${k}: ${v}`)
        .join(', ');
      setResult(summary || 'Merged successfully');
    } catch (err) {
      const e = err as Error;
      setResult(`Error: ${e.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-50" onClick={onClose} />
      <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
        <div
          className="pointer-events-auto bg-[var(--bg-surface-raised)] border border-[var(--border-subtle)] rounded-xl shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border-subtle)] shrink-0">
            <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Merge Contacts
            </h3>
            <button onClick={onClose} className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-4 scrollbar-thin">
            {/* Primary */}
            <div className="p-3 rounded-lg bg-[var(--brand-primary-soft)] border border-[var(--brand-primary)]/30">
              <p className="text-[9px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1">Primary (will be kept)</p>
              <p className="text-xs font-bold text-[var(--text-primary)]">{primary.display_name || primary.name}</p>
              <div className="flex items-center gap-2 mt-1">
                <PlatformBadge platforms={primary.platforms || []} size="xs" />
                <span className="text-[9px] text-[var(--text-muted)]">{primary.msg_count} msgs</span>
              </div>
            </div>

            {!result && (
              <>
                {/* Search for secondary */}
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-[var(--text-muted)] absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search for the contact to merge in..."
                    className="w-full pl-9 pr-4 py-2 bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-lg text-xs text-[var(--text-primary)] outline-none focus:border-primary transition-all"
                  />
                </div>

                {/* Candidates */}
                {candidates.length > 0 && (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {candidates.map((c) => (
                      <button
                        key={c.name}
                        onClick={() => setSelected(c)}
                        className={`w-full flex items-center gap-3 p-2.5 rounded-lg text-left transition-colors border ${
                          selected?.name === c.name
                            ? 'border-[var(--brand-primary)] bg-[var(--brand-primary-soft)]'
                            : 'border-transparent hover:bg-[var(--bg-surface)]'
                        }`}
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-[var(--text-primary)] truncate">{c.display_name || c.name}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <PlatformBadge platforms={c.platforms || []} size="xs" />
                            <span className="text-[9px] text-[var(--text-muted)]">{c.msg_count} msgs</span>
                          </div>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                      </button>
                    ))}
                  </div>
                )}

                {/* Confirm */}
                {selected && (
                  <div className="p-3 rounded-lg bg-amber-400/10 border border-amber-400/20">
                    <p className="text-[10px] font-bold text-amber-400 flex items-center gap-1.5">
                      <AlertTriangle className="w-3 h-3" />
                      This action is irreversible
                    </p>
                    <p className="text-[9px] text-[var(--text-muted)] mt-1">
                      All data from &ldquo;{selected.display_name || selected.name}&rdquo; will be merged into &ldquo;{primary.display_name || primary.name}&rdquo; and the secondary contact will be deleted.
                    </p>
                    <button
                      onClick={handleMerge}
                      disabled={submitting}
                      className="mt-3 w-full py-2 rounded-lg bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white text-xs font-bold transition-colors flex items-center justify-center gap-1.5"
                    >
                      {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                      Confirm Merge
                    </button>
                  </div>
                )}
              </>
            )}

            {/* Result */}
            {result && (
              <div className="p-3 rounded-lg" style={{ background: result.startsWith('Error') ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)', border: `1px solid ${result.startsWith('Error') ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}` }}>
                <p className={`text-xs font-bold ${result.startsWith('Error') ? 'text-red-400' : 'text-emerald-400'}`}>
                  {result.startsWith('Error') ? 'Merge failed' : 'Merge complete'}
                </p>
                <p className="text-[10px] text-[var(--text-muted)] mt-1">{result}</p>
                <button onClick={onMerged} className="mt-3 w-full py-2 rounded-lg bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-strong)] text-white text-xs font-bold transition-colors">
                  Done
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
