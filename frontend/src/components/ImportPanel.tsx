'use client';

/**
 * Import panel — token-driven, drag-and-drop, with clear status and what-to-do.
 */

import React, { useState, useRef, useCallback } from 'react';
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
} from 'lucide-react';

type Status =
  | { kind: 'idle' }
  | { kind: 'success'; text: string }
  | { kind: 'error'; text: string }
  | { kind: 'progress'; text: string };

export default function ImportPanel() {
  const [folderPath, setFolderPath] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<Status>({ kind: 'idle' });
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const fetchTasks = useTaskStore((s) => s.fetchTasks);

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
        <Upload className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
        <h2 className="text-sm font-bold text-[var(--text-primary)]">Import DMs</h2>
      </header>

      <div className="flex-1 overflow-y-auto p-6 max-w-2xl mx-auto w-full">
        {/* Status banner */}
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
            // Pressing Enter focuses the path input as a keyboard equivalent of dropping a folder.
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
          className={`mt-4 p-8 border-2 border-dashed rounded-lg text-center transition-colors cursor-pointer ${
            dragging
              ? 'border-[var(--brand-primary)] bg-[var(--brand-primary-soft)]'
              : 'border-[var(--border-subtle)] bg-[var(--bg-surface)]'
          }`}
        >
          <FileArchive
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
        <div className="mt-5">
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

        {/* What goes here */}
        <section className="mt-6 p-4 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg">
          <h3 className="text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-2 flex items-center gap-1.5">
            <Info className="w-3 h-3" />
            What goes here
          </h3>
          <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed mb-2">
            Point to the <em>parent</em> folder that contains{' '}
            <code className="px-1 py-0.5 rounded bg-[var(--bg-surface-inset)] border border-[var(--border-subtle)] font-mono text-[10px]">
              messages/inbox/
            </code>
            . The importer walks every contact folder, parses monthly JSON, transcribes any
            audio clips, and indexes everything for RAG.
          </p>
          <ul className="text-[11px] text-[var(--text-secondary)] space-y-1 list-disc list-inside leading-relaxed">
            <li>Instagram data export (unzipped)</li>
            <li>Facebook data export (unzipped)</li>
            <li>Custom folders matching the same structure</li>
          </ul>
        </section>

        {/* What happens after */}
        <section className="mt-3 p-4 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg">
          <h3 className="text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3 h-3" style={{ color: 'var(--brand-primary)' }} />
            What happens after import
          </h3>
          <ol className="text-[11px] text-[var(--text-secondary)] space-y-1.5 list-decimal list-inside leading-relaxed">
            <li>JSON messages are parsed into monthly markdown logs.</li>
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
