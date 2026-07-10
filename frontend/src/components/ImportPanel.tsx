'use client';

/**
 * Import panel — token-driven, drag-and-drop, with clear status and what-to-do.
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { apiFetch } from '../store/api';
import { useTaskStore } from '../store/taskStore';
import {
  Upload,
  FolderOpen,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  FileArchive,
  Sparkles,
  Info,
  MessageCircle,
  Database,
  Loader2,
} from 'lucide-react';

type Status =
  | { kind: 'idle' }
  | { kind: 'success'; text: string }
  | { kind: 'error'; text: string }
  | { kind: 'progress'; text: string };

interface WaStatus {
  bridge_online: boolean;
  last_message_at: string | null;
  total_messages: number;
  contacts_count: number;
  pending_merges: number;
}

export default function ImportPanel() {
  const [folderPath, setFolderPath] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<Status>({ kind: 'idle' });
  const [dragging, setDragging] = useState(false);
  const [waStatus, setWaStatus] = useState<WaStatus | null>(null);
  const [waLoading, setWaLoading] = useState(true);
  const [migrating, setMigrating] = useState(false);
  const [migrateResult, setMigrateResult] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fetchTasks = useTaskStore((s) => s.fetchTasks);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await apiFetch<WaStatus>('/whatsapp/status');
        setWaStatus(data);
      } catch {
        setWaStatus(null);
      } finally {
        setWaLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleMigrate = async () => {
    setMigrating(true);
    setMigrateResult(null);
    try {
      const res = await apiFetch<Record<string, number>>('/whatsapp/migrate', {
        method: 'POST',
        body: '{}',
      });
      setMigrateResult(`Migrated: ${res.migrated || 0} messages, ${res.contacts || 0} contacts, ${res.audio_enqueued || 0} audio`);
    } catch (err) {
      const e = err as Error;
      setMigrateResult(`Error: ${e.message}`);
    } finally {
      setMigrating(false);
    }
  };

  const handleImport = useCallback(
    async (path: string) => {
      if (!path.trim()) return;
      setSubmitting(true);
      setStatus({ kind: 'progress', text: 'Starting import…' });
      try {
        await apiFetch('/contacts/import', {
          method: 'POST',
          body: JSON.stringify({ path: path.trim() }),
        });
        setStatus({
          kind: 'success',
          text: 'Import started. Watch the Status Bar (bottom) for progress.',
        });
        setFolderPath('');
        // Trigger task list refresh on the next poll cycle
        fetchTasks();
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Unknown error';
        setStatus({ kind: 'error', text: `Import failed: ${msg}` });
      } finally {
        setSubmitting(false);
      }
    },
    [fetchTasks],
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const items = Array.from(e.dataTransfer.items);
      const folders = items.filter((it) => it.webkitGetAsEntry?.()?.isDirectory);
      if (folders.length > 0) {
        // We can't read the path of a dropped folder in the browser, only the file handle.
        // For now we tell the user to paste the path manually.
        setStatus({
          kind: 'error',
          text: 'Drop detected, but browsers cannot read folder paths. Please paste the full folder path in the field below.',
        });
        return;
      }
      const first = items[0];
      if (first) {
        const entry = first.webkitGetAsEntry?.();
        if (entry?.isFile) {
          setStatus({
            kind: 'error',
            text: 'Please drop the parent folder (the one containing messages/inbox/), not individual files. Use the path field below.',
          });
        }
      }
    },
    [],
  );

  return (
    <div className="h-full flex flex-col overflow-hidden bg-[var(--bg-canvas)]">
      {/* Header */}
      <header className="h-[56px] px-6 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] shrink-0 flex items-center gap-2.5">
        <Database className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
        <h2 className="text-sm font-bold text-[var(--text-primary)]">Data Sources</h2>
      </header>

      <div className="flex-1 overflow-y-auto p-6 w-full max-w-5xl mx-auto">
        {/* ── PLATFORM COLUMNS ──────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* ═══ LEFT COLUMN — WHATSAPP ══════════════════════════════════════ */}
          <section
            className="rounded-xl border bg-[var(--bg-surface)] overflow-hidden"
            style={{ borderColor: 'rgba(37, 211, 102, 0.3)' }}
          >
            {/* Column header */}
            <div
              className="flex items-center gap-2 px-4 py-3 border-b"
              style={{ borderColor: 'rgba(37, 211, 102, 0.25)', background: 'rgba(37, 211, 102, 0.06)' }}
            >
              <MessageCircle className="w-4 h-4" style={{ color: '#25D366' }} />
              <h3 className="text-xs font-bold text-[var(--text-primary)]">WhatsApp</h3>
              <span className="ml-auto text-[9px] text-[var(--text-muted)] font-semibold uppercase tracking-wider">
                Live Bridge
              </span>
            </div>

            <div className="p-4">
              {/* Online indicator */}
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] text-[var(--text-muted)] font-semibold uppercase tracking-wider">
                  Bridge Status
                </span>
                {waLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--text-muted)]" />
                ) : (
                  <span
                    className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-1 rounded-full"
                    style={{
                      background: waStatus?.bridge_online
                        ? 'rgba(37, 211, 102, 0.12)'
                        : 'rgba(239, 68, 68, 0.1)',
                      color: waStatus?.bridge_online ? '#25D366' : '#EF4444',
                    }}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${waStatus?.bridge_online ? 'bg-[#25D366]' : 'bg-[#EF4444]'}`}
                    />
                    {waStatus?.bridge_online ? 'Live' : 'Offline'}
                  </span>
                )}
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-3 gap-2.5 mb-4">
                <div className="p-2.5 rounded-lg bg-[var(--bg-surface-inset)] text-center">
                  <p className="text-base font-bold text-[var(--text-primary)]">
                    {waStatus?.total_messages ?? 0}
                  </p>
                  <p className="text-[9px] text-[var(--text-muted)] mt-0.5">Messages</p>
                </div>
                <div className="p-2.5 rounded-lg bg-[var(--bg-surface-inset)] text-center">
                  <p className="text-base font-bold text-[var(--text-primary)]">
                    {waStatus?.contacts_count ?? 0}
                  </p>
                  <p className="text-[9px] text-[var(--text-muted)] mt-0.5">Contacts</p>
                </div>
                <div className="p-2.5 rounded-lg bg-[var(--bg-surface-inset)] text-center">
                  <p className="text-base font-bold text-[var(--text-primary)]">
                    {waStatus?.pending_merges ?? 0}
                  </p>
                  <p className="text-[9px] text-[var(--text-muted)] mt-0.5">Suggestions</p>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex gap-2 mb-3">
                <button
                  onClick={handleMigrate}
                  disabled={migrating}
                  className="flex-1 py-2 rounded-lg border text-[10px] font-bold transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
                  style={{
                    borderColor: 'rgba(37, 211, 102, 0.3)',
                    color: '#25D366',
                    background: 'rgba(37, 211, 102, 0.06)',
                  }}
                >
                  {migrating ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                  Migrate XML Data
                </button>
                <button
                  onClick={() =>
                    window.open(
                      'https://github.com/anomalyco/Profile-Guru/tree/main/Whatsapp-Bridge',
                      '_blank',
                    )
                  }
                  className="flex-1 py-2 rounded-lg border border-[var(--border-glass)] text-[10px] font-bold text-[var(--text-secondary)] hover:bg-[var(--bg-surface-inset)] transition-colors"
                >
                  Reconnect
                </button>
              </div>

              {migrateResult && (
                <p
                  className={`mb-2 text-[10px] ${migrateResult.startsWith('Error') ? 'text-red-400' : 'text-emerald-400'}`}
                >
                  {migrateResult}
                </p>
              )}

              {/* Instructions */}
              <div className="p-3 rounded-lg bg-[var(--bg-surface-inset)] border border-[var(--border-subtle)]">
                <h4 className="text-[9px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1.5">
                  How it works
                </h4>
                <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed">
                  The WhatsApp Bridge listens for live messages automatically. Run{' '}
                  <code className="px-1 rounded bg-[var(--bg-surface)] font-mono text-[9px]">
                    node listener.js
                  </code>{' '}
                  in{' '}
                  <code className="px-1 rounded bg-[var(--bg-surface)] font-mono text-[9px]">
                    Whatsapp-Bridge/
                  </code>{' '}
                  and scan the QR code. New messages flow in instantly.
                </p>
                <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed mt-1.5">
                  For existing chat history, export WhatsApp chats as XML and use{' '}
                  <span className="font-semibold text-[var(--text-primary)]">Migrate XML Data</span>{' '}
                  above to bulk-import them.
                </p>
              </div>
            </div>
          </section>

          {/* ═══ RIGHT COLUMN — INSTAGRAM ═══════════════════════════════════ */}
          <section
            className="rounded-xl border bg-[var(--bg-surface)] overflow-hidden"
            style={{ borderColor: 'rgba(225, 48, 108, 0.3)' }}
          >
            {/* Column header */}
            <div
              className="flex items-center gap-2 px-4 py-3 border-b"
              style={{ borderColor: 'rgba(225, 48, 108, 0.25)', background: 'rgba(225, 48, 108, 0.06)' }}
            >
              <FileArchive className="w-4 h-4" style={{ color: '#E1306C' }} />
              <h3 className="text-xs font-bold text-[var(--text-primary)]">Instagram</h3>
              <span className="ml-auto text-[9px] text-[var(--text-muted)] font-semibold uppercase tracking-wider">
                Folder Import
              </span>
            </div>

            <div className="p-4">
              {/* Status banners (Instagram import feedback) */}
              {status.kind === 'success' ? (
                <Banner kind="success" icon={<CheckCircle2 className="w-3.5 h-3.5" />}>
                  {status.text}
                </Banner>
              ) : null}
              {status.kind === 'error' ? (
                <Banner kind="error" icon={<AlertCircle className="w-3.5 h-3.5" />}>
                  {status.text}
                </Banner>
              ) : null}
              {status.kind === 'progress' ? (
                <Banner kind="info" icon={<RefreshCw className="w-3.5 h-3.5 animate-spin" />}>
                  {status.text}
                </Banner>
              ) : null}

              {/* Drag-and-drop zone */}
              <div
                role="button"
                tabIndex={0}
                aria-label="Drag and drop import folder, or use the path field below"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    inputRef.current?.focus();
                  }
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                className={`p-6 border-2 border-dashed rounded-lg text-center transition-colors cursor-pointer ${
                  status.kind === 'success' ||
                  status.kind === 'error' ||
                  status.kind === 'progress'
                    ? 'mt-3'
                    : ''
                } ${
                  dragging
                    ? 'border-[var(--brand-primary)] bg-[var(--brand-primary-soft)]'
                    : 'border-[var(--border-subtle)] bg-[var(--bg-surface)]'
                }`}
              >
                <Upload
                  className="w-8 h-8 mx-auto mb-2"
                  style={{ color: dragging ? 'var(--brand-primary)' : 'var(--text-muted)' }}
                />
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  Drop your export folder here
                </p>
                <p className="text-[11px] text-[var(--text-muted)] mt-1">
                  or paste the full path below
                </p>
              </div>

              {/* Path input */}
              <div className="mt-4">
                <label
                  htmlFor="import-path"
                  className="block text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1.5"
                >
                  Export folder path
                </label>
                <div className="flex gap-2">
                  <input
                    ref={inputRef}
                    id="import-path"
                    value={folderPath}
                    onChange={(e) => setFolderPath(e.target.value)}
                    placeholder="C:\Users\You\Downloads\instagram-export"
                    autoComplete="off"
                    spellCheck={false}
                    className="flex-1 h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--brand-primary)] font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => handleImport(folderPath)}
                    disabled={submitting || !folderPath.trim()}
                    className="h-9 px-4 inline-flex items-center gap-1.5 text-xs font-semibold rounded-md border transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-white"
                    style={{
                      background: 'var(--brand-primary)',
                      borderColor: 'var(--brand-primary-strong)',
                    }}
                  >
                    {submitting ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <FolderOpen className="w-3.5 h-3.5" />
                    )}
                    Import
                  </button>
                </div>
              </div>

              {/* Instagram-specific hint */}
              <div className="mt-4 p-3 rounded-lg bg-[var(--bg-surface-inset)] border border-[var(--border-subtle)]">
                <h4 className="text-[9px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1.5">
                  How to get your export
                </h4>
                <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed">
                  Visit Instagram →{' '}
                  <span className="font-semibold text-[var(--text-primary)]">
                    Settings → Your Account → Data Download
                  </span>{' '}
                  and request a copy. Once received, unzip it and point the path above at the
                  folder containing{' '}
                  <code className="px-1 rounded bg-[var(--bg-surface)] font-mono text-[9px]">
                    messages/inbox/
                  </code>
                  .
                </p>
              </div>
            </div>
          </section>
        </div>

        {/* ── FULL-WIDTH INFO SECTIONS (shared) ──────────────────────────── */}
        <section className="mt-6 p-4 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg">
          <h3 className="text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-2 flex items-center gap-1.5">
            <Info className="w-3 h-3" />
            What goes here
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] font-bold text-[#25D366] mb-1">WhatsApp</p>
              <ul className="text-[11px] text-[var(--text-secondary)] space-y-1 list-disc list-inside leading-relaxed">
                <li>Live messages via WhatsApp Bridge (auto-connected)</li>
                <li>Exported chat XML files for bulk history migration</li>
              </ul>
            </div>
            <div>
              <p className="text-[10px] font-bold text-[#E1306C] mb-1">Instagram / Facebook</p>
              <ul className="text-[11px] text-[var(--text-secondary)] space-y-1 list-disc list-inside leading-relaxed">
                <li>
                  Instagram data export (unzipped) — folder containing{' '}
                  <code className="px-1 py-0.5 rounded bg-[var(--bg-surface-inset)] border border-[var(--border-subtle)] font-mono text-[10px]">
                    messages/inbox/
                  </code>
                </li>
                <li>Facebook data export (unzipped)</li>
                <li>Custom folders matching the same structure</li>
              </ul>
            </div>
          </div>
        </section>

        <section className="mt-3 p-4 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg">
          <h3 className="text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3 h-3" style={{ color: 'var(--brand-primary)' }} />
            What happens after import
          </h3>
          <ol className="text-[11px] text-[var(--text-secondary)] space-y-1.5 list-decimal list-inside leading-relaxed">
            <li>JSON / XML messages are parsed into monthly markdown logs.</li>
            <li>Voice clips are transcribed (Whisper local / Gemini cloud).</li>
            <li>Every chunk is embedded into the local RAG index.</li>
            <li>Connection analytics are precomputed.</li>
            <li>You can open any contact and run a personality assessment.</li>
          </ol>
        </section>
      </div>
    </div>
  );
}

function Banner({
  kind,
  icon,
  children,
}: {
  kind: 'success' | 'error' | 'info';
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  const styles =
    kind === 'success'
      ? { bg: 'rgba(61,214,140,0.06)', border: 'rgba(61,214,140,0.3)', color: 'var(--success)' }
      : kind === 'error'
      ? { bg: 'rgba(255,90,95,0.06)', border: 'rgba(255,90,95,0.3)', color: 'var(--error)' }
      : { bg: 'var(--brand-primary-soft)', border: 'var(--brand-primary)', color: 'var(--brand-primary)' };

  return (
    <div
      role={kind === 'error' ? 'alert' : 'status'}
      className="p-2.5 rounded-md border text-xs flex items-center gap-2"
      style={{ background: styles.bg, borderColor: styles.border, color: styles.color }}
    >
      {icon}
      <span>{children}</span>
    </div>
  );
}
