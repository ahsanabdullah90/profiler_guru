'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useStatusStore } from '../store/statusStore';
import { useTaskStore, Task } from '../store/taskStore';
import { StatusService } from '../services/StatusService';
import {
  Cpu, RefreshCw, Layers, Globe, Server, ChevronUp, ChevronDown,
  Trash2, BarChart3, Search, XCircle, CheckCircle, AlertCircle, Loader2
} from 'lucide-react';

const TaskRow = React.memo(function TaskRow({ task, onCancel }: { task: Task; onCancel: (id: string) => void }) {
  const pct = task.total > 0 ? Math.round((task.current / task.total) * 100) : 0;
  const elapsed = Date.now() / 1000 - task.start_time;
  const mins = Math.floor(elapsed / 60);
  const secs = Math.floor(elapsed % 60);
  const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;

  const statusIcon = task.status === 'running' ? (
    <Loader2 className="w-3.5 h-3.5 animate-spin text-[#007AFF]" />
  ) : task.status === 'completed' ? (
    <CheckCircle className="w-3.5 h-3.5 text-[#32D74B]" />
  ) : task.status === 'failed' ? (
    <AlertCircle className="w-3.5 h-3.5 text-[#FF375F]" />
  ) : (
    <Loader2 className="w-3.5 h-3.5 animate-spin text-[#FF9500]" />
  );

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b border-[var(--border-glass)] last:border-0">
      {statusIcon}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-zinc-200 truncate">{task.name}</span>
          <span className="text-[10px] text-zinc-500 font-mono">{timeStr}</span>
        </div>
        {task.total > 0 && (
          <div className="mt-1.5 flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-[var(--primary)] rounded-full transition-all duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-[10px] text-zinc-500 font-mono w-12 text-right">
              {task.current}/{task.total}
            </span>
          </div>
        )}
        {task.error && (
          <p className="text-[10px] text-[#FF375F] mt-1 truncate">{task.error}</p>
        )}
      </div>
      {task.status === 'running' && (
        <button
          onClick={() => onCancel(task.id)}
          className="p-1 rounded hover:bg-zinc-800 text-zinc-500 hover:text-[#FF375F] transition-colors"
          title="Cancel task"
        >
          <XCircle className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
});

export default function ProgressPanel() {
  const status = useStatusStore(s => s.status);
  const setStatus = useStatusStore(s => s.setStatus);
  const tasks = useTaskStore(s => s.tasks);
  const expanded = useTaskStore(s => s.expanded);
  const setExpanded = useTaskStore(s => s.setExpanded);
  const fetchTasks = useTaskStore(s => s.fetchTasks);
  const submitVacuum = useTaskStore(s => s.submitVacuum);
  const submitAnalytics = useTaskStore(s => s.submitAnalytics);
  const submitReindex = useTaskStore(s => s.submitReindex);
  const cancelTask = useTaskStore(s => s.cancelTask);
  const serviceRef = useRef<StatusService | null>(null);
  const [submitting, setSubmitting] = useState<string | null>(null);

  useEffect(() => {
    const service = new StatusService((update) => setStatus(update));
    serviceRef.current = service;
    service.start();

    // Fetch initial task list on mount
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
      // Error handled by store
    } finally {
      setSubmitting(null);
    }
  };

  const isRunning = (type: string) =>
    tasks.some((t) => t.id === type && t.status === 'running');

  return (
    <footer
      className={`w-full border-t border-[var(--border-glass)] bg-[rgba(10,10,12,0.6)] backdrop-blur-md relative z-30 transition-all duration-300 ease-in-out ${
        expanded ? 'h-[300px]' : 'h-[40px]'
      }`}
    >
      {/* Compact Mode: Always visible */}
      <button
        className="h-[40px] px-6 flex items-center justify-between text-[11px] font-medium text-zinc-400 select-none font-sans w-full"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Left Area: Connection & Background Sync Monitor */}
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${status.app_online ? 'bg-[#32D74B] animate-led-pulse' : 'bg-[#FF375F]'}`} />
            <span className="font-bold text-zinc-300">
              App: {status.app_online ? 'Online' : 'Offline'}
            </span>
          </div>

        </div>

        {/* Middle Area: Heavy Task Queues */}
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2">
            <Cpu className={`w-3.5 h-3.5 ${status.transcription.status === 'transcribing' ? 'text-[#FF9500] animate-pulse' : 'text-zinc-500'}`} />
            {status.transcription.status === 'transcribing' ? (
              <span>
                Transcribing: <strong className="text-[#FF9500]">{status.transcription.contact}</strong>
                {status.transcription.total > 0 && (
                  <span className="text-zinc-500 ml-1">
                    ({status.transcription.current}/{status.transcription.total} clips)
                  </span>
                )}
              </span>
            ) : (
              <span>Transcribing: <strong className="text-zinc-500">Idle</strong></span>
            )}
          </div>

          <div className="hidden sm:flex items-center gap-2 border-l border-zinc-800 pl-5">
            <Layers className={`w-3.5 h-3.5 ${status.rag.status === 'indexing' ? 'text-[#007AFF] animate-bounce' : 'text-zinc-500'}`} />
            {status.rag.status === 'indexing' ? (
              <span>
                RAG: <strong className="text-[#007AFF]">Indexing {status.rag.contact}</strong>
                <span className="text-zinc-500 ml-1">({status.rag.progress}%)</span>
              </span>
            ) : (
              <span>RAG: <strong className="text-zinc-500">Upto Date</strong></span>
            )}
          </div>
          {/* Always show a compact RAG icon on small screens */}
          <div className="flex sm:hidden items-center gap-2">
            <Layers className={`w-3.5 h-3.5 ${status.rag.status === 'indexing' ? 'text-[#007AFF] animate-bounce' : 'text-zinc-500'}`} />
          </div>
        </div>

        {/* Right Area: LLM + Task Count + Expand */}
        <div className="flex items-center gap-3 sm:gap-5 border-l border-zinc-800 pl-3 sm:pl-5">
          <div className="flex items-center gap-1.5">
            <Globe className="w-3.5 h-3.5 text-zinc-500" />
            <span className="hidden sm:inline">Cloud ({status.online_llm.model}):</span>
            <span className={`font-bold ${status.online_llm.online ? 'text-[#32D74B]' : 'text-[#FF375F]'}`}>
              {status.online_llm.online ? 'Online' : 'Offline'}
            </span>
          </div>

          <div className="hidden md:flex items-center gap-1.5 border-l border-zinc-800 pl-3 sm:pl-5">
            <Server className="w-3.5 h-3.5 text-zinc-500" />
            <span>Ollama ({status.ollama.model}):</span>
            <span className={`font-bold ${status.ollama.online ? 'text-[#32D74B]' : 'text-[#FF375F]'}`}>
              {status.ollama.online ? 'Online' : 'Offline'}
            </span>
          </div>

          {hasRunning && (
            <span className="px-1.5 py-0.5 bg-[var(--primary)] text-white text-[10px] font-bold rounded-full">
              {runningTasks.length}
            </span>
          )}

          <div className="pl-2">
            {expanded ? <ChevronDown className="w-4 h-4 text-zinc-500" /> : <ChevronUp className="w-4 h-4 text-zinc-500" />}
          </div>
        </div>
      </button>

      {/* Expanded Mode: Task List + Submit Buttons */}
      {expanded && (
        <div className="h-[260px] flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto scrollbar-thin">
            {tasks.length === 0 ? (
              <div className="flex items-center justify-center h-full text-zinc-600 text-xs italic">
                No background tasks running
              </div>
            ) : (
              <>
                {runningTasks.length > 0 && (
                  <div>
                    <div className="px-4 py-1.5 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                      Active
                    </div>
                    {runningTasks.map((task) => (
                      <TaskRow key={task.id} task={task} onCancel={cancelTask} />
                    ))}
                  </div>
                )}
                {recentTasks.length > 0 && (
                  <div>
                    <div className="px-4 py-1.5 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                      Recent
                    </div>
                    {recentTasks.map((task) => (
                      <TaskRow key={task.id} task={task} onCancel={cancelTask} />
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Submit Section */}
          <div className="h-[60px] px-4 py-2.5 border-t border-[var(--border-glass)] flex items-center gap-3 shrink-0">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mr-2">Run:</span>
            <button
              onClick={() => handleSubmit('vacuum')}
              disabled={isRunning('vacuum_orphans') || submitting === 'vacuum'}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[rgba(255,255,255,0.03)] border border-[var(--border-glass)] rounded-lg text-[11px] font-semibold text-zinc-300 hover:bg-[rgba(255,255,255,0.06)] hover:border-zinc-700 disabled:opacity-40 disabled:pointer-events-none transition-all"
            >
              <Trash2 className="w-3 h-3" />
              {submitting === 'vacuum' ? 'Submitting...' : 'Vacuum Vectors'}
            </button>
            <button
              onClick={() => handleSubmit('analytics')}
              disabled={isRunning('precompute_analytics') || submitting === 'analytics'}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[rgba(255,255,255,0.03)] border border-[var(--border-glass)] rounded-lg text-[11px] font-semibold text-zinc-300 hover:bg-[rgba(255,255,255,0.06)] hover:border-zinc-700 disabled:opacity-40 disabled:pointer-events-none transition-all"
            >
              <BarChart3 className="w-3 h-3" />
              {submitting === 'analytics' ? 'Submitting...' : 'Precompute Analytics'}
            </button>
            <button
              onClick={() => handleSubmit('reindex')}
              disabled={isRunning('reindex_rag') || submitting === 'reindex'}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[rgba(255,255,255,0.03)] border border-[var(--border-glass)] rounded-lg text-[11px] font-semibold text-zinc-300 hover:bg-[rgba(255,255,255,0.06)] hover:border-zinc-700 disabled:opacity-40 disabled:pointer-events-none transition-all"
            >
              <Search className="w-3 h-3" />
              {submitting === 'reindex' ? 'Submitting...' : 'Reindex RAG'}
            </button>
          </div>
        </div>
      )}
    </footer>
  );
}
