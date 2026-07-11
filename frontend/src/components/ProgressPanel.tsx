'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useStatusStore } from '../store/statusStore';
import { useTaskStore, Task } from '../store/taskStore';
import { StatusService } from '../services/StatusService';
import { shallow } from 'zustand/shallow';
import {
  Cpu,
  Layers,
  Globe,
  Server,
  ChevronUp,
  ChevronDown,
  Trash2,
  BarChart3,
  Search,
  XCircle,
  CheckCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';

/** Returns the current time, updating every `intervalMs`. Avoids impure calls during render. */
function useTickingNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

const TaskRow = React.memo(function TaskRow({
  task,
  onCancel,
  nowMs,
}: {
  task: Task;
  onCancel: (id: string) => void;
  nowMs: number;
}) {
  const pct = task.total > 0 ? Math.round((task.current / task.total) * 100) : 0;
  const elapsed = nowMs / 1000 - task.start_time;
  const mins = Math.floor(elapsed / 60);
  const secs = Math.floor(elapsed % 60);
  const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;

  const statusIcon =
    task.status === 'running' ? (
      <Loader2
        className="w-3.5 h-3.5 animate-spin"
        style={{ color: 'var(--brand-primary)' }}
      />
    ) : task.status === 'completed' ? (
      <CheckCircle className="w-3.5 h-3.5" style={{ color: 'var(--success)' }} />
    ) : task.status === 'failed' ? (
      <AlertCircle className="w-3.5 h-3.5" style={{ color: 'var(--error)' }} />
    ) : (
      <Loader2
        className="w-3.5 h-3.5 animate-spin"
        style={{ color: 'var(--warning)' }}
      />
    );

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b border-[var(--border-subtle)] last:border-0">
      {statusIcon}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--text-primary)] truncate">
            {task.name}
          </span>
          <span className="text-[10px] text-[var(--text-muted)] font-mono">{timeStr}</span>
        </div>
        {task.total > 0 && (
          <div className="mt-1.5 flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-[var(--bg-surface-inset)] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{ width: `${pct}%`, background: 'var(--brand-primary)' }}
              />
            </div>
            <span className="text-[10px] text-[var(--text-muted)] font-mono w-12 text-right">
              {task.current}/{task.total}
            </span>
          </div>
        )}
        {task.error && (
          <p
            className="text-[10px] mt-1 truncate"
            style={{ color: 'var(--error)' }}
          >
            {task.error}
          </p>
        )}
      </div>
      {task.status === 'running' && (
        <button
          type="button"
          onClick={() => onCancel(task.id)}
          className="p-1 rounded text-[var(--text-muted)] hover:text-[var(--error)] hover:bg-[var(--bg-surface)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-2"
          title="Cancel task"
          aria-label={`Cancel task ${task.name}`}
        >
          <XCircle className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
});

/** StatusBar — 28px collapsed footer with system status; expands to 200px for task list. */
export default function ProgressPanel() {
  const status = useStatusStore((s) => ({
    app_online: s.status.app_online,
    transcription: s.status.transcription,
    rag: s.status.rag,
    online_llm: s.status.online_llm,
    ollama: s.status.ollama,
  }), shallow);
  const setStatus = useStatusStore((s) => s.setStatus);
  const tasks = useTaskStore((s) => s.tasks);
  const expanded = useTaskStore((s) => s.expanded);
  const setExpanded = useTaskStore((s) => s.setExpanded);
  const fetchTasks = useTaskStore((s) => s.fetchTasks);
  const submitVacuum = useTaskStore((s) => s.submitVacuum);
  const submitAnalytics = useTaskStore((s) => s.submitAnalytics);
  const submitReindex = useTaskStore((s) => s.submitReindex);
  const cancelTask = useTaskStore((s) => s.cancelTask);
  const serviceRef = useRef<StatusService | null>(null);
  const [submitting, setSubmitting] = useState<string | null>(null);
  const nowMs = useTickingNow(30_000);

  useEffect(() => {
    const service = new StatusService((update) => setStatus(update));
    serviceRef.current = service;
    service.start();
    fetchTasks();
    return () => {
      service.stop();
      serviceRef.current = null;
    };
  }, [setStatus, fetchTasks]);

  const runningTasks = useMemo(() => tasks.filter((t) => t.status === 'running'), [tasks]);
  const recentTasks = useMemo(() => tasks.filter((t) => t.status !== 'running'), [tasks]);
  const hasRunning = runningTasks.length > 0;

  const handleSubmit = async (type: 'vacuum' | 'analytics' | 'reindex') => {
    setSubmitting(type);
    try {
      if (type === 'vacuum') await submitVacuum();
      else if (type === 'analytics') await submitAnalytics();
      else await submitReindex();
    } catch {
      /* Error handled by store */
    } finally {
      setSubmitting(null);
    }
  };

  const isRunning = (type: string) =>
    tasks.some((t) => t.id === type && t.status === 'running');

  const timeStr = new Date(nowMs).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <footer
      role="contentinfo"
      aria-label="System status and task queue"
      className="w-full border-t border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] relative z-30 transition-all duration-200 ease-in-out"
      style={{ height: expanded ? 200 : 28 }}
    >
      {/* Compact Mode — 28px */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-controls="statusbar-expanded"
        className="h-[28px] px-4 flex items-center justify-between text-[10px] font-medium text-[var(--text-muted)] w-full hover:bg-[var(--bg-surface)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--brand-primary)] focus-visible:outline-offset-[-2px]"
      >
        {/* Left: connection */}
        <div className="flex items-center gap-4 min-w-0">
          <div className="flex items-center gap-1.5">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                status.app_online ? 'animate-led-pulse' : ''
              }`}
              style={{
                background: status.app_online ? 'var(--success)' : 'var(--error)',
              }}
              aria-hidden="true"
            />
            <span className="font-bold text-[var(--text-secondary)]">
              {status.app_online ? 'Online' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Middle: tasks */}
        <div className="flex items-center gap-4 min-w-0">
          <div className="flex items-center gap-1.5">
            <Cpu
              className="w-3 h-3"
              style={{
                color:
                  status.transcription.status === 'transcribing'
                    ? 'var(--warning)'
                    : 'var(--text-muted)',
              }}
            />
            {status.transcription.status === 'transcribing' ? (
              <span>
                <span className="text-[var(--text-muted)]">Transcribing </span>
                <strong style={{ color: 'var(--warning)' }}>
                  {status.transcription.contact}
                </strong>
                {status.transcription.total > 0 && (
                  <span className="text-[var(--text-muted)] ml-1 font-mono">
                    {status.transcription.current}/{status.transcription.total}
                  </span>
                )}
              </span>
            ) : (
              <span className="text-[var(--text-muted)]">
                Transcribing <strong className="text-[var(--text-muted)]">Idle</strong>
              </span>
            )}
          </div>

          <div className="hidden sm:flex items-center gap-1.5 border-l border-[var(--border-subtle)] pl-4">
            <Layers
              className="w-3 h-3"
              style={{
                color:
                  status.rag.status === 'indexing'
                    ? 'var(--brand-primary)'
                    : status.rag.status === 'needs_indexing'
                    ? '#F59E0B'
                    : 'var(--text-muted)',
              }}
            />
            {status.rag.status === 'indexing' ? (
              <span title={status.rag.warning || undefined} className="flex items-center gap-1">
                <span className="text-[var(--text-muted)]">RAG </span>
                <strong style={{ color: 'var(--brand-primary)' }}>
                  {status.rag.warning ? 'Re-indexing (Model Upgrade)' : `Indexing ${status.rag.contact}`}
                </strong>
                <span className="text-[var(--text-muted)] ml-1 font-mono">
                  {status.rag.progress}%
                </span>
                {status.rag.warning && (
                  <span className="ml-1.5 text-[9px] text-amber-400 font-bold animate-pulse" title={status.rag.warning}>
                    ⚠️ Let embeddings complete
                  </span>
                )}
              </span>
            ) : status.rag.status === 'needs_indexing' ? (
              <span className="flex items-center gap-1">
                <span className="text-[var(--text-muted)]">RAG </span>
                <strong style={{ color: '#F59E0B' }}>Index Required</strong>
              </span>
            ) : (
              <span className="text-[var(--text-muted)]">
                RAG <strong className="text-[var(--text-muted)]">Up to date</strong>
              </span>
            )}
          </div>
        </div>

        {/* Right: engines + queue count + clock + expand */}
        <div className="flex items-center gap-3 border-l border-[var(--border-subtle)] pl-3 min-w-0">
          <div className="hidden md:flex items-center gap-1.5">
            <Globe className="w-3 h-3 text-[var(--text-muted)]" />
            <span
              className="font-bold"
              style={{
                color: status.online_llm.online ? 'var(--success)' : 'var(--text-muted)',
              }}
            >
              {status.online_llm.online ? 'Cloud' : 'Cloud off'}
            </span>
          </div>

          <div className="hidden lg:flex items-center gap-1.5">
            <Server className="w-3 h-3 text-[var(--text-muted)]" />
            <span
              className="font-bold"
              style={{
                color: status.ollama.online ? 'var(--success)' : 'var(--text-muted)',
              }}
            >
              {status.ollama.online ? 'Local' : 'Local off'}
            </span>
          </div>

          {hasRunning ? (
            <span
              className="px-1.5 py-0.5 text-[9px] font-bold rounded-full text-white"
              style={{ background: 'var(--brand-primary)' }}
              aria-label={`${runningTasks.length} running tasks`}
            >
              {runningTasks.length}
            </span>
          ) : null}

          <span
            className="hidden md:inline text-[var(--text-muted)] font-mono"
            suppressHydrationWarning
          >
            {timeStr}
          </span>

          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)]" />
          ) : (
            <ChevronUp className="w-3.5 h-3.5 text-[var(--text-muted)]" />
          )}
        </div>
      </button>

      {/* Expanded Mode — task list + actions */}
      {expanded ? (
        <div
          id="statusbar-expanded"
          className="h-[172px] flex flex-col overflow-hidden border-t border-[var(--border-subtle)]"
        >
          <div className="flex-1 overflow-y-auto scrollbar-thin">
            {tasks.length === 0 ? (
              <div className="flex items-center justify-center h-full text-[var(--text-muted)] text-xs italic">
                No background tasks
              </div>
            ) : (
              <>
                {runningTasks.length > 0 ? (
                  <div>
                    <div className="px-4 py-1.5 text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-wider">
                      Active
                    </div>
                    {runningTasks.map((task) => (
                      <TaskRow key={task.id} task={task} onCancel={cancelTask} nowMs={nowMs} />
                    ))}
                  </div>
                ) : null}
                {recentTasks.length > 0 ? (
                  <div>
                    <div className="px-4 py-1.5 text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-wider">
                      Recent
                    </div>
                    {recentTasks.map((task) => (
                      <TaskRow key={task.id} task={task} onCancel={cancelTask} nowMs={nowMs} />
                    ))}
                  </div>
                ) : null}
              </>
            )}
          </div>

          <div className="h-[44px] px-4 flex items-center gap-2 shrink-0 border-t border-[var(--border-subtle)]">
            <span className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-wider mr-1">
              Run:
            </span>
            <button
              type="button"
              onClick={() => handleSubmit('vacuum')}
              disabled={isRunning('vacuum_orphans') || submitting === 'vacuum'}
              className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-semibold rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Trash2 className="w-3 h-3" />
              {submitting === 'vacuum' ? 'Submitting…' : 'Vacuum Vectors'}
            </button>
            <button
              type="button"
              onClick={() => handleSubmit('analytics')}
              disabled={isRunning('precompute_analytics') || submitting === 'analytics'}
              className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-semibold rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <BarChart3 className="w-3 h-3" />
              {submitting === 'analytics' ? 'Submitting…' : 'Precompute Analytics'}
            </button>
            <button
              type="button"
              onClick={() => handleSubmit('reindex')}
              disabled={isRunning('reindex_rag') || submitting === 'reindex'}
              className={`h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-semibold rounded-md border disabled:opacity-40 disabled:cursor-not-allowed transition-all ${
                status.rag.status === 'needs_indexing'
                  ? 'border-amber-500/50 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 hover:border-amber-400 hover:text-amber-300 shadow-[0_0_8px_rgba(245,158,11,0.15)] animate-pulse'
                  : 'border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]'
              }`}
            >
              <Search className="w-3 h-3" />
              {submitting === 'reindex' ? 'Submitting…' : 'Reindex RAG'}
            </button>
          </div>
        </div>
      ) : null}
    </footer>
  );
}
