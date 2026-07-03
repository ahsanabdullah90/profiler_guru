import { create } from 'zustand';
import { apiFetch } from './api';

export interface Task {
  id: string;
  name: string;
  current: number;
  total: number;
  status: 'running' | 'completed' | 'failed' | 'cancelling';
  start_time: number;
  error: string | null;
  task_type: string;
  description: string;
}

interface TaskState {
  tasks: Task[];
  expanded: boolean;

  setExpanded: (expanded: boolean) => void;
  fetchTasks: () => Promise<void>;
  submitVacuum: () => Promise<void>;
  submitAnalytics: () => Promise<void>;
  submitReindex: () => Promise<void>;
  cancelTask: (id: string) => Promise<void>;
}

export const useTaskStore = create<TaskState>((set, get) => {
  let intervalId: ReturnType<typeof setInterval> | null = null;

  const startPolling = () => {
    if (intervalId) return;
    intervalId = setInterval(() => {
      get().fetchTasks();
    }, 3000);
  };

  const stopPolling = () => {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  };

  return {
    tasks: [],
    expanded: false,

    setExpanded: (expanded: boolean) => {
      set({ expanded });
      if (expanded) {
        get().fetchTasks();
        startPolling();
      } else {
        stopPolling();
      }
    },

    fetchTasks: async () => {
      try {
        const data = await apiFetch<{ tasks: Task[] }>('/tasks', { timeout: 5000 });
        set({ tasks: data.tasks });
      } catch {
        // Silently fail — tasks are non-critical
      }
    },

    submitVacuum: async () => {
      try {
        await apiFetch('/tasks/vacuum', { method: 'POST', timeout: 10000 });
        get().fetchTasks();
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'Failed to submit vacuum task';
        throw new Error(msg);
      }
    },

    submitAnalytics: async () => {
      try {
        await apiFetch('/tasks/analytics', { method: 'POST', timeout: 10000 });
        get().fetchTasks();
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'Failed to submit analytics task';
        throw new Error(msg);
      }
    },

    submitReindex: async () => {
      try {
        await apiFetch('/tasks/reindex', { method: 'POST', timeout: 10000 });
        get().fetchTasks();
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'Failed to submit reindex task';
        throw new Error(msg);
      }
    },

    cancelTask: async (id: string) => {
      try {
        await apiFetch(`/tasks/${id}`, { method: 'DELETE', timeout: 5000 });
        get().fetchTasks();
      } catch {
        // Silently fail
      }
    },
  };
});
