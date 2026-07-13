import { create } from 'zustand';
import { apiFetch, type ProfileMeta, type GlobalSearchResult, type RagChatError } from './api';
import { useStatusStore } from './statusStore';
import { useContactsStore, resolveChatName } from './contactsStore';
import { getApiBase, getAuthToken } from '../lib/apiConfig';

export interface AssessmentJob {
  job_id: string;
  contact_name: string;
  framework_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'cancelling';
  progress: number;
  progress_message: string;
  queue_position: number;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  error_message: string | null;
}

interface RagState {
  savedProfile: string | null;
  profileMeta: ProfileMeta | null;
  isGeneratingProfile: boolean;
  isQueryingRAG: boolean;
  ragChatHistory: { sender: 'user' | 'ai'; text: string; time: string; error?: RagChatError; sources?: string[] }[];
  isGlobalSearchOpen: boolean;
  globalSearchQuery: string;
  globalSearchResults: GlobalSearchResult[];
  activeSearchController: AbortController | null;
  activeProfileController: AbortController | null;

  // Assessment jobs
  jobs: Record<string, AssessmentJob>;
  activeJobId: string | null;
  generationError: string | null;
  setGenerationError: (err: string | null) => void;

  setGlobalSearchOpen: (open: boolean) => void;
  setGlobalSearchQuery: (query: string) => void;
  fetchProfile: (contact: string, signal?: AbortSignal) => Promise<void>;
  generateProfile: (contact: string, startMonth: string, endMonth: string, forceCloud: boolean, deepScan: boolean, userConsent: boolean, modelProvider?: string, modelName?: string, frameworkId?: string) => Promise<void>;
  queryRAG: (contact: string, query: string, startMonth: string | null, endMonth: string | null, deepScan: boolean, userConsent: boolean) => Promise<void>;
  globalSearch: (query: string) => Promise<void>;
  clearProfile: () => void;
  cancelProfileGeneration: () => Promise<void>;
  refreshJobs: () => Promise<void>;
  getJobForContact: (contact: string) => AssessmentJob | null;
}

let jobPollInterval: ReturnType<typeof setInterval> | null = null;

function startJobPolling(getState: () => RagState, setState: (partial: Partial<RagState>) => void) {
  if (jobPollInterval) return;
  jobPollInterval = setInterval(async () => {
    try {
      const data = await apiFetch<{ jobs: AssessmentJob[] }>('/rag/jobs', { timeout: 5000 });
      const jobsMap: Record<string, AssessmentJob> = {};
      for (const job of data.jobs) {
        jobsMap[job.job_id] = job;
      }
      const prev = getState().jobs;
      setState({ jobs: jobsMap });

      // Check for newly completed jobs — auto-load if showing that contact
      for (const job of data.jobs) {
        const prevJob = prev[job.job_id];
        if (prevJob && prevJob.status !== 'completed' && job.status === 'completed') {
          useStatusStore.getState().pushError(`Assessment complete for ${job.contact_name}`, 'info');
          const currentContact = useContactsStore.getState().selectedContact;
          const resolvedName = currentContact ? resolveChatName(currentContact) : null;
          if (currentContact && (resolvedName === job.contact_name || currentContact === job.contact_name)) {
            getState().fetchProfile(currentContact);
          }
          if (getState().activeJobId === job.job_id) {
            setState({ activeJobId: null, isGeneratingProfile: false });
          }
        }
        if (prevJob && prevJob.status !== 'failed' && job.status === 'failed') {
          useStatusStore.getState().pushError(`Assessment failed for ${job.contact_name}: ${job.error_message || 'Unknown error'}`, 'error');
          if (getState().activeJobId === job.job_id) {
            setState({ activeJobId: null, isGeneratingProfile: false, generationError: job.error_message || 'Unknown error' });
          }
        }
        if (prevJob && prevJob.status !== 'cancelled' && job.status === 'cancelled') {
          if (getState().activeJobId === job.job_id) {
            setState({ activeJobId: null, isGeneratingProfile: false });
          }
        }
      }

      // Auto-stop polling if no active jobs
      const hasActive = data.jobs.some((j) => j.status === 'queued' || j.status === 'running' || j.status === 'cancelling');
      if (!hasActive && jobPollInterval) {
        clearInterval(jobPollInterval);
        jobPollInterval = null;
      }
    } catch {
      // Silently fail
    }
  }, 2000);
}

export const useRagStore = create<RagState>((set, get) => ({
  savedProfile: null,
  profileMeta: null,
  isGeneratingProfile: false,
  isQueryingRAG: false,
  ragChatHistory: [],
  isGlobalSearchOpen: false,
  globalSearchQuery: '',
  globalSearchResults: [],
  activeSearchController: null,
  activeProfileController: null,
  jobs: {},
  activeJobId: null,
  generationError: null,
  setGenerationError: (generationError) => set({ generationError }),

  setGlobalSearchOpen: (isGlobalSearchOpen) => set({ isGlobalSearchOpen }),
  setGlobalSearchQuery: (globalSearchQuery) => set({ globalSearchQuery }),
  clearProfile: () => set({
    savedProfile: null,
    profileMeta: null,
    generationError: null,
    isGeneratingProfile: false,
    activeJobId: null,
    ragChatHistory: [],
  }),

  fetchProfile: async (contact, signal) => {
    try {
      const data = await apiFetch<{ profile: string | null; meta: ProfileMeta | null }>(`/rag/contacts/${contact}/profile`, { signal });
      if (data && (data.profile === null || data.profile === '')) {
        set({ savedProfile: null, profileMeta: null });
      } else {
        set({ savedProfile: data.profile, profileMeta: data.meta });
      }
    } catch (err) {
      const e = err as Error;
      if (e.name === 'AbortError') return;
      useStatusStore.getState().pushError(`Failed to load profile for ${contact}: ${e.message}`, 'warning');
    }
  },

  generateProfile: async (contact, startMonth, endMonth, _forceCloud, _deepScan, userConsent, modelProvider?, modelName?, frameworkId?) => {
    set({ isGeneratingProfile: true, generationError: null });
    try {
      const body: Record<string, unknown> = {
        start_month: startMonth,
        end_month: endMonth,
        user_consent: userConsent,
        framework_id: frameworkId || 'communication_style',
      };
      if (modelProvider && modelName) {
        body.model_provider = modelProvider;
        body.model_name = modelName;
      }
      const data = await apiFetch<{ job_id: string; status: string }>(`/rag/contacts/${contact}/profile`, {
        method: 'POST',
        body: JSON.stringify(body),
        timeout: 10000,
      });

      const now = Date.now() / 1000;
      const newJob: AssessmentJob = {
        job_id: data.job_id,
        contact_name: contact,
        framework_id: frameworkId || 'communication_style',
        status: 'queued',
        progress: 0,
        progress_message: 'Submitted',
        queue_position: 0,
        created_at: now,
        started_at: null,
        completed_at: null,
        error_message: null,
      };
      set({
        activeJobId: data.job_id,
        generationError: null,
        jobs: { ...get().jobs, [data.job_id]: newJob },
      });
      startJobPolling(get, set);
    } catch (err) {
      const e = err as Error;
      useStatusStore.getState().pushError(`Failed to generate profile: ${e.message}`, 'error');
      set({ isGeneratingProfile: false, generationError: e.message });
    }
  },

  cancelProfileGeneration: async () => {
    const jobId = get().activeJobId;
    if (!jobId) return;
    try {
      await apiFetch(`/rag/jobs/${jobId}`, { method: 'DELETE', timeout: 5000 });
    } catch {
      // Server-side cancel may fail if job already completed — still clear local state
    }
    const updatedJobs = { ...get().jobs };
    delete updatedJobs[jobId];
    set({ activeJobId: null, isGeneratingProfile: false, generationError: null, jobs: updatedJobs });
  },

  refreshJobs: async () => {
    try {
      const data = await apiFetch<{ jobs: AssessmentJob[] }>('/rag/jobs', { timeout: 5000 });
      const jobsMap: Record<string, AssessmentJob> = {};
      for (const job of data.jobs) {
        jobsMap[job.job_id] = job;
      }
      set({ jobs: jobsMap });
      const hasActive = data.jobs.some((j) => j.status === 'queued' || j.status === 'running' || j.status === 'cancelling');
      if (!hasActive) {
        set({ isGeneratingProfile: false, activeJobId: null });
      }
    } catch {
      // Silently fail
    }
  },

  getJobForContact: (contact: string) => {
    const jobs = Object.values(get().jobs);
    const resolvedName = resolveChatName(contact) || contact;
    const contactJobs = jobs.filter((j) => j.contact_name === resolvedName);
    if (contactJobs.length === 0) return null;
    return contactJobs.reduce((latest, j) =>
      j.created_at > latest.created_at ? j : latest
    );
  },

  queryRAG: async (contact, query, startMonth, endMonth, deepScan, userConsent) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    set((state) => ({
      isQueryingRAG: true,
      ragChatHistory: [...state.ragChatHistory, { sender: 'user', text: query, time: timeStr }],
    }));

    try {
      const token = getAuthToken();
      const apiBase = getApiBase();
      const response = await fetch(`${apiBase}/rag/contacts/${contact}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          query,
          start_month: startMonth,
          end_month: endMonth,
          deep_scan: deepScan,
          user_consent: userConsent,
        }),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson?.detail?.message || errJson?.detail || response.statusText);
      }

      if (!response.body) {
        throw new Error("No response body received from stream.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentAiMsgIndex = -1;

      const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      set((state) => {
        const nextHistory = [...state.ragChatHistory, { sender: 'ai' as const, text: '', time: responseTimeStr, sources: [] }];
        currentAiMsgIndex = nextHistory.length - 1;
        return { ragChatHistory: nextHistory };
      });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;
          const dataStr = trimmed.slice(6);
          if (dataStr === '{"type": "done"}') continue;

          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.type === 'metadata') {
              set((state) => {
                if (currentAiMsgIndex === -1) return {};
                const nextHistory = [...state.ragChatHistory];
                const msg = nextHistory[currentAiMsgIndex];
                if (msg) {
                  msg.sources = parsed.sources || [];
                }
                return { ragChatHistory: nextHistory };
              });
            } else if (parsed.type === 'token') {
              set((state) => {
                if (currentAiMsgIndex === -1) return {};
                const nextHistory = [...state.ragChatHistory];
                const msg = nextHistory[currentAiMsgIndex];
                if (msg) {
                  msg.text += parsed.text;
                }
                return { ragChatHistory: nextHistory };
              });
            } else if (parsed.type === 'error') {
              throw new Error(parsed.message || 'Stream error');
            }
          } catch {
            // Ignore unparseable SSE lines
          }
        }
      }
    } catch (err) {
      const e = err as Error;
      useStatusStore.getState().pushError(`RAG query failed: ${e.message}`, 'error');
      const responseTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      set((state) => {
        const nextHistory = [...state.ragChatHistory];
        const lastMsg = nextHistory[nextHistory.length - 1];
        if (lastMsg && lastMsg.sender === 'ai' && !lastMsg.error) {
          lastMsg.text = e.message || 'LLM query failed.';
          lastMsg.error = {
            message: e.message || 'LLM query failed.',
            can_retry: true,
            query,
            start_month: startMonth,
            end_month: endMonth,
            deep_scan: deepScan,
            user_consent: userConsent
          };
          return { ragChatHistory: nextHistory };
        } else {
          return {
            ragChatHistory: [
              ...nextHistory,
              {
                sender: 'ai' as const,
                text: e.message || 'LLM query failed.',
                time: responseTimeStr,
                error: {
                  message: e.message || 'LLM query failed.',
                  can_retry: true,
                  query,
                  start_month: startMonth,
                  end_month: endMonth,
                  deep_scan: deepScan,
                  user_consent: userConsent
                }
              }
            ]
          };
        }
      });

    } finally {
      set({ isQueryingRAG: false });
    }
  },

  globalSearch: async (query) => {
    const currentController = get().activeSearchController;
    if (currentController) {
      currentController.abort();
    }

    if (!query.trim()) {
      set({ globalSearchResults: [], activeSearchController: null });
      return;
    }

    const newController = new AbortController();
    set({ activeSearchController: newController });

    try {
      const data = await apiFetch<GlobalSearchResult[]>('/rag/search', {
        method: 'POST',
        body: JSON.stringify({ query }),
        signal: newController.signal,
      });
      if (get().globalSearchQuery !== query) return;
      set({ globalSearchResults: data });
    } catch (err) {
      const e = err as Error;
      if (e.name === 'AbortError') return;
      if (get().globalSearchQuery !== query) return;
      useStatusStore.getState().pushError(`Global search failed: ${e.message}`, 'warning');
    } finally {
      if (get().activeSearchController === newController) {
        set({ activeSearchController: null });
      }
    }
  },
}));
