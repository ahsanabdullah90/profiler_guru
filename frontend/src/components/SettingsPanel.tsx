'use client';

/**
 * Settings panel — token-driven, grouped (Data / Models / About).
 * Fetches /api/v1/settings on mount and persists changes via POST.
 */

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { apiFetch } from '../store/api';
import { useUIStore } from '../store/uiStore';
import Button from './ui/Button';
import Surface from './ui/Surface';
import {
  Settings as SettingsIcon,
  Save,
  RefreshCw,
  Database,
  Cpu,
  Info,
  Check,
  AlertCircle,
  FileText,
  Zap,
  BarChart3,
  MessageSquare,
  RotateCcw,
  Crown,
  Lock,
} from 'lucide-react';
import FeatureGate, { TierBadge, useFeatureGate, type FeatureProvider } from './FeatureGate';

interface SettingsData {
  // Provider selection
  active_provider: string;
  ollama_model: string;
  gemini_model: string;
  anthropic_model: string;
  openai_model: string;
  opencode_go_model: string;
  opencode_zen_model: string;
  // API keys (masked)
  gemini_api_key: string;
  anthropic_api_key: string;
  openai_api_key: string;
  opencode_go_api_key: string;
  opencode_zen_api_key: string;
  // Embedding
  embedding_provider: string;
  embedding_model: string;
  // Legacy
  cloud_provider: string;
  cloud_api_key: string;
  llm_provider: string;
  // Existing
  deep_scan_default: boolean;
  pdf_include_charts: boolean;
  pdf_include_raw_snippets: boolean;
  pdf_include_textual_profile: boolean;
  report_sections_order: string[];
  rag_relevancy_threshold: number;
  rag_token_budget_ollama: number;
  rag_token_budget_gemini: number;
  assessment_min_blocks: number;
  instagram_username?: string;
  display_name?: string;
  prompt_overrides?: Record<string, { system: string; user: string }>;
}

interface SettingsResponse {
  settings: SettingsData;
  installed_ollama_models: string[];
  best_local_model: string | null;
}

type Group = 'provider' | 'analysis' | 'reports' | 'prompts' | 'subscription' | 'about';

type ConnectionStatus = 'idle' | 'testing' | 'success' | 'error';

const PROVIDERS: { value: string; label: string }[] = [
  { value: 'ollama', label: 'Ollama (Local)' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'anthropic', label: 'Anthropic Claude' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'opencode_go', label: 'OpenCode Go' },
  { value: 'opencode_zen', label: 'OpenCode Zen' },
];

export default function SettingsPanel() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [initialSettings, setInitialSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [activeGroup, setActiveGroup] = useState<Group>('provider');
  const [connectionStatus, setConnectionStatus] = useState<Record<string, ConnectionStatus>>({});
  const [availableModels, setAvailableModels] = useState<Record<string, string[]>>({});
  const [testError, setTestError] = useState<Record<string, string>>({});
  const [showProviders, setShowProviders] = useState(false);
  const [embeddingWarning, setEmbeddingWarning] = useState<{
    key: 'embedding_provider' | 'embedding_model';
    value: string;
  } | null>(null);
  const theme = useUIStore((s) => s.theme);

  useEffect(() => {
    let mounted = true;
    apiFetch('/settings')
      .then((res: unknown) => {
        if (!mounted) return;
        const payload = res as SettingsResponse;
        // Auto-select embedding model if Ollama provider and empty
        if (
          payload.settings.embedding_provider === 'ollama' &&
          !payload.settings.embedding_model &&
          payload.installed_ollama_models.length > 0
        ) {
          const preferred = payload.installed_ollama_models.find((m) =>
            /bge|nomic|mxbai|gte|snowflake|minilm|all/i.test(m)
          );
          payload.settings.embedding_model =
            preferred || payload.best_local_model || payload.installed_ollama_models[0];
        }
        setData(payload);
        setInitialSettings(JSON.parse(JSON.stringify(payload.settings)));
        setLoading(false);
      })
      .catch(() => {
        if (!mounted) return;
        setMessage({ type: 'error', text: 'Failed to load settings' });
        setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const hasUnsavedChanges = useMemo(() => {
    if (!data || !initialSettings) return false;
    return JSON.stringify(data.settings) !== JSON.stringify(initialSettings);
  }, [data, initialSettings]);

  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    setMessage(null);
    try {
      await apiFetch('/settings', {
        method: 'POST',
        body: JSON.stringify({ settings: data.settings }),
      });
      setInitialSettings(JSON.parse(JSON.stringify(data.settings)));
      setMessage({ type: 'success', text: 'Settings saved' });
      setTimeout(() => setMessage(null), 3000);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setMessage({ type: 'error', text: `Save failed: ${msg}` });
    } finally {
      setSaving(false);
    }
  };

  const testConnection = useCallback(async (provider: string) => {
    if (!data) return;
    setConnectionStatus(prev => ({ ...prev, [provider]: 'testing' }));
    setTestError(prev => ({ ...prev, [provider]: '' }));
    const keyMap: Record<string, string> = {
      gemini: 'gemini_api_key',
      anthropic: 'anthropic_api_key',
      openai: 'openai_api_key',
      opencode_go: 'opencode_go_api_key',
      opencode_zen: 'opencode_zen_api_key',
    };
    const apiKey = data.settings[keyMap[provider] as keyof SettingsData] as string || '';
    try {
      const res = await apiFetch<{ success: boolean; models?: string[]; error?: string }>('/settings/test-connection', {
        method: 'POST',
        body: JSON.stringify({ provider, api_key: apiKey }),
      });
      if (res.success) {
        setConnectionStatus(prev => ({ ...prev, [provider]: 'success' }));
        if (res.models) {
          setAvailableModels(prev => ({ ...prev, [provider]: res.models! }));
        }
      } else {
        setConnectionStatus(prev => ({ ...prev, [provider]: 'error' }));
        setTestError(prev => ({ ...prev, [provider]: res.error || 'Connection failed' }));
      }
    } catch (e) {
      setConnectionStatus(prev => ({ ...prev, [provider]: 'error' }));
      setTestError(prev => ({ ...prev, [provider]: e instanceof Error ? e.message : 'Connection failed' }));
    }
  }, [data]);

  const update = <K extends keyof SettingsData>(key: K, value: SettingsData[K]) => {
    if (!data) return;
    setData({ ...data, settings: { ...data.settings, [key]: value } });
  };

  const renderProviderConfig = useCallback((provider: string) => {
    const keyMap: Record<string, string> = {
      gemini: 'gemini_api_key',
      anthropic: 'anthropic_api_key',
      openai: 'openai_api_key',
      opencode_go: 'opencode_go_api_key',
      opencode_zen: 'opencode_zen_api_key',
    };
    const key = keyMap[provider] as keyof SettingsData;
    const status = connectionStatus[provider] || 'idle';
    const errMsg = testError[provider] || '';

    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <input
            id={`${provider}-api-key`}
            type="password"
            value={(data?.settings[key] as string) || ''}
            onChange={(e) => update(key as keyof SettingsData, e.target.value)}
            placeholder="Enter API key"
            className="flex-1 h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--brand-primary)] font-mono"
          />
          <button
            type="button"
            onClick={() => testConnection(provider)}
            disabled={status === 'testing'}
            className="h-9 px-3 inline-flex items-center gap-1.5 text-[10px] font-semibold rounded-md border transition-colors disabled:opacity-40"
            style={{
              background: 'var(--bg-surface-raised)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-primary)',
            }}
          >
            {status === 'testing' ? (
              <RefreshCw className="w-3 h-3 animate-spin" />
            ) : (
              <Zap className="w-3 h-3" />
            )}
            Test
          </button>
        </div>
        {errMsg ? (
          <p className="text-[10px] text-rose-400">{errMsg}</p>
        ) : null}
        {status === 'success' && (availableModels[provider] || []).length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-emerald-400">
              {availableModels[provider]!.length} models available
            </span>
          </div>
        )}
      </div>
    );
  }, [data, connectionStatus, availableModels, testError, testConnection, update]);

  const renderConnectionBadge = useCallback((provider: string) => {
    const status = connectionStatus[provider] || 'idle';
    if (status === 'idle') return null;
    if (status === 'testing') return <span className="text-[10px] text-amber-400 animate-pulse">Testing…</span>;
    if (status === 'success') return <span className="text-[10px] text-emerald-400">✅ Connected</span>;
    return <span className="text-[10px] text-rose-400">❌ Failed</span>;
  }, [connectionStatus]);

  const requestEmbeddingChange = (
    key: 'embedding_provider' | 'embedding_model',
    value: string
  ) => {
    if (!data) return;
    const current = data.settings[key];
    if (value !== current) {
      setEmbeddingWarning({ key, value });
    }
  };

  const confirmEmbeddingChange = () => {
    if (!data || !embeddingWarning) return;
    update(embeddingWarning.key as keyof SettingsData, embeddingWarning.value);
    setEmbeddingWarning(null);
  };

  const cancelEmbeddingChange = () => {
    setEmbeddingWarning(null);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-[var(--bg-canvas)]">
        <div className="flex flex-col items-center gap-2 text-[var(--text-muted)]">
          <RefreshCw className="w-5 h-5 animate-spin" style={{ color: 'var(--brand-primary)' }} />
          <span className="text-xs">Loading settings…</span>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="h-full flex items-center justify-center bg-[var(--bg-canvas)] p-6">
        <div className="max-w-md text-center space-y-3">
          <AlertCircle className="w-6 h-6 mx-auto" style={{ color: 'var(--error)' }} />
          <p className="text-sm text-[var(--text-primary)]">Unable to load settings.</p>
          {message ? (
            <p className="text-xs text-[var(--text-muted)]">{message.text}</p>
          ) : null}
          <Button onClick={() => window.location.reload()} variant="secondary" size="sm">
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const { settings, installed_ollama_models, best_local_model } = data;

  return (
    <div className="h-full flex flex-col overflow-hidden bg-[var(--bg-canvas)]">
      {/* Header */}
      <header className="h-[56px] px-6 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] shrink-0 flex items-center">
        <div className="flex items-center gap-2.5">
          <SettingsIcon className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
          <h2 className="text-sm font-bold text-[var(--text-primary)]">Settings</h2>
        </div>
      </header>

      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Group nav */}
        <nav
          aria-label="Settings sections"
          className="w-[200px] border-r border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 shrink-0"
        >
          <GroupButton
            icon={<Zap className="w-3.5 h-3.5" />}
            label="Provider"
            active={activeGroup === 'provider'}
            onClick={() => setActiveGroup('provider')}
          />
          <GroupButton
            icon={<BarChart3 className="w-3.5 h-3.5" />}
            label="Analysis"
            active={activeGroup === 'analysis'}
            onClick={() => setActiveGroup('analysis')}
          />
          <GroupButton
            icon={<FileText className="w-3.5 h-3.5" />}
            label="Reports"
            active={activeGroup === 'reports'}
            onClick={() => setActiveGroup('reports')}
          />
          <GroupButton
            icon={<MessageSquare className="w-3.5 h-3.5" />}
            label="Prompts"
            active={activeGroup === 'prompts'}
            onClick={() => setActiveGroup('prompts')}
          />
          <GroupButton
            icon={<Crown className="w-3.5 h-3.5" />}
            label="Plan"
            active={activeGroup === 'subscription'}
            onClick={() => setActiveGroup('subscription')}
          />
          <GroupButton
            icon={<Info className="w-3.5 h-3.5" />}
            label="About"
            active={activeGroup === 'about'}
            onClick={() => setActiveGroup('about')}
          />
        </nav>

        {/* Group content */}
        <div className="flex-1 overflow-y-auto p-6 bg-[var(--bg-canvas)]">
          {message ? (
            <div
              role={message.type === 'error' ? 'alert' : 'status'}
              className="mb-4 p-2.5 rounded-md border text-xs flex items-center gap-2"
              style={
                message.type === 'error'
                  ? {
                      background: 'rgba(255, 90, 95, 0.06)',
                      borderColor: 'rgba(255, 90, 95, 0.3)',
                      color: 'var(--error)',
                    }
                  : {
                      background: 'rgba(61, 214, 140, 0.06)',
                      borderColor: 'rgba(61, 214, 140, 0.3)',
                      color: 'var(--success)',
                    }
              }
            >
              {message.type === 'error' ? (
                <AlertCircle className="w-3.5 h-3.5" />
              ) : (
                <Check className="w-3.5 h-3.5" />
              )}
              {message.text}
            </div>
          ) : null}

          {activeGroup === 'provider' ? (
            <Section title="Provider" description="Choose your AI service and configure API keys.">
              <Field
                label="Active Provider"
                description="Choose which AI service powers your profile generation and analysis."
              >
                <select
                  id="active-provider"
                  value={data.settings.active_provider || 'ollama'}
                  onChange={(e) => update('active_provider', e.target.value)}
                  className="w-full h-9 px-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)]"
                >
                  {PROVIDERS.map((p) => (
                    <option key={p.value} value={p.value}>{p.label}</option>
                  ))}
                </select>
              </Field>

              {data.settings.active_provider === 'ollama' ? (
                <div className="p-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] space-y-3">
                  <div className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-semibold text-emerald-400">
                      {data.installed_ollama_models.length > 0
                        ? `Connected (${data.installed_ollama_models.length} models installed)`
                        : 'Ollama not detected — no models found'}
                    </span>
                  </div>
                  <Field label="Model">
                    <select
                      value={data.settings.ollama_model || ''}
                      onChange={(e) => update('ollama_model', e.target.value)}
                      className="w-full h-9 px-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)]"
                    >
                      <option value="" disabled={data.installed_ollama_models.length > 0}>
                        {data.installed_ollama_models.length > 0 ? '— Select a model —' : 'No models detected'}
                      </option>
                      {data.installed_ollama_models.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </Field>
                  {data.settings.ollama_model && data.best_local_model && data.settings.ollama_model === data.best_local_model ? (
                    <p className="text-[10px] text-emerald-400">Auto-selected recommended model.</p>
                  ) : data.best_local_model ? (
                    <p className="text-[10px] text-[var(--text-muted)]">
                      Recommended:{' '}
                      <button
                        type="button"
                        onClick={() => update('ollama_model', data.best_local_model!)}
                        className="font-mono font-semibold hover:underline"
                        style={{ color: 'var(--brand-primary)' }}
                      >
                        {data.best_local_model}
                      </button>
                    </p>
                  ) : null}
                </div>
              ) : (
                <div className="p-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] space-y-3">
                  {renderProviderConfig(data.settings.active_provider)}
                </div>
              )}

              {data.settings.active_provider !== 'ollama' && (
                <div className="mt-3">
                  <Field
                    label="Model"
                    description={
                      connectionStatus[data.settings.active_provider] === 'success'
                        ? 'Select a model from your account.'
                        : 'Test the connection above to see available models.'
                    }
                  >
                    <select
                      value={(data.settings)[`${data.settings.active_provider}_model` as keyof SettingsData] as string || ''}
                      onChange={(e) => update(`${data.settings.active_provider}_model` as keyof SettingsData, e.target.value)}
                      disabled={connectionStatus[data.settings.active_provider] !== 'success'}
                      className="w-full h-9 px-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)] disabled:opacity-50"
                    >
                      <option value="" disabled>
                        {connectionStatus[data.settings.active_provider] === 'success'
                          ? '— Select a model —'
                          : 'Test connection first'}
                      </option>
                      {(availableModels[data.settings.active_provider] || []).map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </Field>
                </div>
              )}

              <div className="mt-6 pt-4 border-t border-[var(--border-subtle)]">
                <button
                  type="button"
                  onClick={() => setShowProviders((s) => !s)}
                  className="w-full flex items-center justify-between text-xs font-bold text-[var(--text-primary)] mb-3"
                >
                  <span>Other Providers</span>
                  <span className="text-[10px] text-[var(--text-muted)]">
                    {showProviders ? 'Hide' : 'Show'}
                  </span>
                </button>
                {showProviders && (
                  <div className="space-y-3">
                    {PROVIDERS.filter(p => p.value !== data.settings.active_provider && p.value !== 'ollama').map((p) => (
                      <div key={p.value} className="p-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                        <div className="flex items-center justify-between mb-2">
                          <h5 className="text-[11px] font-bold text-[var(--text-primary)]">{p.label}</h5>
                          {renderConnectionBadge(p.value)}
                        </div>
                        {renderProviderConfig(p.value)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Section>
          ) : null}

          {activeGroup === 'analysis' ? (
            <Section title="Analysis" description="Control how profiles are generated and how embeddings work.">
              <Field
                label="Deep Scan by Default"
                description="Run thorough RAG scans on first profile generation."
              >
                <Switch
                  checked={settings.deep_scan_default}
                  onChange={(v) => update('deep_scan_default', v)}
                  label="Deep scan"
                />
              </Field>
              <Field
                label="Minimum Assessment Chat Volume (Message Blocks)"
                description="Minimum conversational message blocks required to generate a profile."
              >
                <input
                  id="assessment-min-blocks"
                  type="number"
                  min="1"
                  max="100"
                  step="1"
                  value={data.settings.assessment_min_blocks ?? 5}
                  onChange={(e) => update('assessment_min_blocks', parseInt(e.target.value) || 5)}
                  className="w-full h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)] font-mono"
                />
              </Field>

              <div className="pt-4 mt-4 border-t border-[var(--border-subtle)]">
                <h4 className="text-xs font-bold text-[var(--text-primary)] mb-3">RAG Pipeline Parameters</h4>
                <Field
                  label="Relevancy Threshold"
                  description="Similarity score threshold (0.0 to 1.0) below which vector chunks are excluded from prompt context."
                >
                  <div className="flex items-center gap-3">
                    <input
                      id="rag-relevancy-threshold-slider"
                      type="range"
                      min="0"
                      max="1.0"
                      step="0.05"
                      value={data.settings.rag_relevancy_threshold ?? 0.3}
                      onChange={(e) => update('rag_relevancy_threshold', parseFloat(e.target.value))}
                      className="w-2/3 h-1.5 rounded-lg appearance-none cursor-pointer bg-[var(--bg-surface-inset)] accent-[var(--brand-primary)]"
                    />
                    <span className="text-xs font-mono font-bold w-12 text-center py-1 rounded bg-[var(--bg-surface-raised)] border border-[var(--border-subtle)]">
                      {data.settings.rag_relevancy_threshold ?? 0.3}
                    </span>
                  </div>
                </Field>
                <Field
                  label="Local Context Budget (Characters)"
                  description="Maximum character length of assembled context text sent to local Ollama queries."
                >
                  <input
                    id="rag-token-budget-ollama"
                    type="number"
                    min="1000"
                    max="100000"
                    step="1000"
                    value={data.settings.rag_token_budget_ollama ?? 15000}
                    onChange={(e) => update('rag_token_budget_ollama', parseInt(e.target.value) || 15000)}
                    className="w-full h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)] font-mono"
                  />
                </Field>
                <Field
                  label="Cloud Context Budget (Characters)"
                  description="Maximum character length of assembled context text sent to cloud queries."
                >
                  <input
                    id="rag-token-budget-gemini"
                    type="number"
                    min="5000"
                    max="1000000"
                    step="5000"
                    value={data.settings.rag_token_budget_gemini ?? 300000}
                    onChange={(e) => update('rag_token_budget_gemini', parseInt(e.target.value) || 300000)}
                    className="w-full h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)] font-mono"
                  />
                </Field>
              </div>

              <div className="pt-4 mt-4 border-t border-[var(--border-subtle)]">
                <h4 className="text-xs font-bold text-[var(--text-primary)] mb-1">Embeddings</h4>
                <p className="text-[10px] text-[var(--text-muted)] mb-3 leading-relaxed">
                  The embedding model turns your text into vectors for search. Changing it requires rebuilding all stored knowledge.
                </p>
                <Field
                  label="Embedding Provider"
                  description="Local uses built-in embeddings. Ollama uses a model running on your machine."
                >
                  <select
                    value={data.settings.embedding_provider || 'ollama'}
                    onChange={(e) => requestEmbeddingChange('embedding_provider', e.target.value)}
                    className="w-full h-9 px-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)]"
                  >
                    <option value="ollama">Ollama (local)</option>
                    <option value="local">Local built-in</option>
                  </select>
                </Field>
                <Field
                  label="Embedding Model"
                  description={
                    data.settings.embedding_provider === 'ollama'
                      ? 'Name of the Ollama model used for embeddings (e.g. bge-m3, nomic-embed-text).'
                      : 'Built-in embedding model is used automatically.'
                  }
                >
                  <select
                    value={data.settings.embedding_model || ''}
                    onChange={(e) => requestEmbeddingChange('embedding_model', e.target.value)}
                    disabled={data.settings.embedding_provider !== 'ollama'}
                    className="w-full h-9 px-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)] disabled:opacity-50"
                  >
                    <option value="">{data.settings.embedding_provider === 'ollama' ? '— Select a model —' : 'Built-in'}</option>
                    {data.installed_ollama_models.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </Field>
              </div>
            </Section>
          ) : null}

          {activeGroup === 'reports' ? (
            <Section title="Reports" description="Control what's included in exported PDF reports.">
              <Field label="Include Charts">
                <Switch
                  checked={settings.pdf_include_charts}
                  onChange={(v) => update('pdf_include_charts', v)}
                  label="Charts in PDF"
                />
              </Field>
              <Field label="Include Raw Snippets">
                <Switch
                  checked={settings.pdf_include_raw_snippets}
                  onChange={(v) => update('pdf_include_raw_snippets', v)}
                  label="Raw snippets in PDF"
                />
              </Field>
              <Field label="Include Textual Profile">
                <Switch
                  checked={settings.pdf_include_textual_profile}
                  onChange={(v) => update('pdf_include_textual_profile', v)}
                  label="Textual profile in PDF"
                />
              </Field>
            </Section>
          ) : null}

          {activeGroup === 'prompts' ? (
            <PromptsSection
              settings={settings}
              update={update}
              onSave={handleSave}
            />
          ) : null}

          {activeGroup === 'subscription' ? (
            <SubscriptionSection />
          ) : null}

          {activeGroup === 'about' ? (
            <Section title="About" description="Theme, account info, and system details.">
              <div className="p-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] space-y-2">
                <span className="text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)]">
                  Active Provider
                </span>
                <p className="text-xs text-[var(--text-primary)]">
                  {PROVIDERS.find((p) => p.value === data.settings.active_provider)?.label || data.settings.active_provider}
                </p>
                {(() => {
                  const modelKey = `${data.settings.active_provider}_model` as keyof SettingsData;
                  const modelVal = data.settings[modelKey];
                  return typeof modelVal === 'string' && modelVal ? (
                    <p className="text-[10px] text-[var(--text-muted)] font-mono">
                      Model: {modelVal}
                    </p>
                  ) : null;
                })()}
              </div>

              <div className="p-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] space-y-3">
                <div className="space-y-1.5">
                  <label className="text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)]">
                    Your Name
                  </label>
                  <input
                    type="text"
                    value={data.settings.display_name || ''}
                    onChange={(e) => update('display_name', e.target.value)}
                    placeholder="e.g. Ahsan"
                    className="w-full h-9 px-3 bg-[var(--bg-canvas)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--brand-primary)] font-mono"
                  />
                  <p className="text-[9px] text-[var(--text-muted)]">The name your messages appear under in chat logs</p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)]">
                    Instagram Username
                  </label>
                  <input
                    type="text"
                    value={data.settings.instagram_username || ''}
                    onChange={(e) => update('instagram_username', e.target.value)}
                    placeholder="e.g. ahsan.javed"
                    className="w-full h-9 px-3 bg-[var(--bg-canvas)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--brand-primary)] font-mono"
                  />
                  <p className="text-[9px] text-[var(--text-muted)]">Used to identify your messages in conversations</p>
                </div>
              </div>

              <div className="p-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                <span className="text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)]">
                  Theme
                </span>
                <p className="text-xs text-[var(--text-primary)] font-mono mt-1">{theme}</p>
              </div>
            </Section>
          ) : null}

          {/* Sticky save bar */}
          <div className="sticky bottom-0 mt-8 pt-4 pb-2 bg-[var(--bg-canvas)] border-t border-[var(--border-subtle)] flex items-center justify-end gap-3">
            {hasUnsavedChanges && (
              <span className="text-[10px] text-amber-400">Unsaved changes</span>
            )}
            <Button onClick={handleSave} loading={saving} variant="primary" size="sm">
              <Save className="w-3.5 h-3.5" />
              Save
            </Button>
          </div>
        </div>
      </div>

      {embeddingWarning && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] p-5 shadow-lg">
            <h3 className="text-sm font-bold text-[var(--text-primary)] mb-2">Rebuild embeddings?</h3>
            <p className="text-[11px] text-[var(--text-muted)] leading-relaxed mb-4">
              Changing the embedding model will regenerate all RAG vector embeddings. This may take several minutes depending on how much data you have stored.
            </p>
            <div className="flex justify-end gap-2">
              <Button onClick={cancelEmbeddingChange} variant="secondary" size="sm">
                Cancel
              </Button>
              <Button onClick={confirmEmbeddingChange} variant="primary" size="sm">
                Proceed
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function GroupButton({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      className={`w-full h-9 px-3 mb-1 flex items-center gap-2 text-xs font-semibold rounded-md transition-colors text-left ${
        active
          ? 'bg-[var(--brand-primary-soft)] text-[var(--brand-primary)]'
          : 'text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)] hover:text-[var(--text-primary)]'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Surface variant="flat" className="p-5 max-w-2xl">
      <header className="mb-4">
        <h3 className="text-sm font-bold text-[var(--text-primary)]">{title}</h3>
        {description ? (
          <p className="text-[11px] text-[var(--text-muted)] mt-1">{description}</p>
        ) : null}
      </header>
      <div className="space-y-4">{children}</div>
    </Surface>
  );
}

function Field({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider font-bold text-[var(--text-muted)] mb-1">
        {label}
      </label>
      {children}
      {description ? (
        <p className="text-[10px] text-[var(--text-muted)] mt-1 leading-relaxed">{description}</p>
      ) : null}
    </div>
  );
}

function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <label className="inline-flex items-center gap-2.5 cursor-pointer">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className="relative w-9 h-5 rounded-full transition-colors"
        style={{
          background: checked ? 'var(--brand-primary)' : 'var(--bg-surface-inset)',
          border: `1px solid ${checked ? 'var(--brand-primary)' : 'var(--border-subtle)'}`,
        }}
      >
        <span
          aria-hidden="true"
          className="absolute top-0.5 w-3.5 h-3.5 rounded-full transition-transform bg-white"
          style={{ transform: `translateX(${checked ? '16px' : '2px'})` }}
        />
      </button>
      <span className="text-xs text-[var(--text-primary)]">{label}</span>
    </label>
  );
}


const PROMPT_FRAMEWORKS = [
  { id: 'communication_style', label: 'Conversation Pattern Analysis' },
  { id: 'big_five', label: 'Big Five / OCEAN' },
  { id: 'attachment', label: 'Attachment Style' },
  { id: 'emotional_intelligence', label: 'Emotional Intelligence' },
];

interface PromptsSectionProps {
  settings: SettingsData;
  update: <K extends keyof SettingsData>(key: K, value: SettingsData[K]) => void;
  onSave: () => Promise<void>;
}

function PromptsSection({ settings, update, onSave }: PromptsSectionProps) {
  const [selectedFw, setSelectedFw] = useState('communication_style');
  const [localOverrides, setLocalOverrides] = useState<Record<string, { system: string; user: string }>>(
    () => (settings.prompt_overrides as Record<string, { system: string; user: string }> | undefined) || {},
  );

  const currentOverride = localOverrides[selectedFw] || { system: '', user: '' };

  const handleChange = (field: 'system' | 'user', value: string) => {
    setLocalOverrides((prev) => {
      const next = { ...prev };
      const existing = next[selectedFw];
      next[selectedFw] = { ...(existing || { system: '', user: '' }), [field]: value };
      return next;
    });
  };

  const handleReset = () => {
    const next = { ...localOverrides };
    delete next[selectedFw];
    setLocalOverrides(next);
  };

  const applyAndSave = async () => {
    update('prompt_overrides' as keyof SettingsData, localOverrides as SettingsData['prompt_overrides']);
    await onSave();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-[var(--text-primary)]">Prompt Templates</h3>
      </div>
      <p className="text-[10px] text-[var(--text-muted)] leading-relaxed">
        Override the system and user prompts for each assessment framework.
        Leave empty to use the built-in defaults. Variables: {'{sender_ctx}'}, {'{name}'}, {'{markdown_snippets}'}, {'{total_messages}'}, {'{avg_sentiment}'}, {'{kb_context}'}, {'{dimension_list}'}.
      </p>

      {/* Framework selector */}
      <div className="flex gap-1.5 flex-wrap">
        {PROMPT_FRAMEWORKS.map((fw) => (
          <button
            key={fw.id}
            type="button"
            onClick={() => setSelectedFw(fw.id)}
            className="px-2.5 py-1 rounded-lg text-[10px] font-bold cursor-pointer transition-all"
            style={{
              background: selectedFw === fw.id ? 'var(--brand-primary)' : 'var(--bg-surface-raised)',
              border: `1px solid ${selectedFw === fw.id ? 'var(--brand-primary)' : 'var(--border-subtle)'}`,
              color: selectedFw === fw.id ? '#fff' : 'var(--text-secondary)',
            }}
          >
            {fw.label}
          </button>
        ))}
      </div>

      {/* System prompt */}
      <div className="flex flex-col gap-1">
        <label className="text-[9px] uppercase font-bold text-[var(--text-muted)]">
          System Prompt
          <span className="text-[var(--text-muted)] font-normal normal-case ml-1">
            (must contain {'{sender_ctx}'})
          </span>
        </label>
        <textarea
          value={currentOverride.system}
          onChange={(e) => handleChange('system', e.target.value)}
          rows={6}
          className="w-full px-3 py-2 rounded-lg text-[11px] font-mono leading-relaxed resize-y outline-none focus:border-[var(--brand-primary)]"
          style={{
            background: 'var(--bg-surface-inset)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-primary)',
            minHeight: '120px',
          }}
          placeholder="Leave empty to use the built-in system prompt for this framework."
        />
      </div>

      {/* User prompt */}
      <div className="flex flex-col gap-1">
        <label className="text-[9px] uppercase font-bold text-[var(--text-muted)]">
          User Prompt
          <span className="text-[var(--text-muted)] font-normal normal-case ml-1">
            (must contain {'{name}'}, {'{markdown_snippets}'})
          </span>
        </label>
        <textarea
          value={currentOverride.user}
          onChange={(e) => handleChange('user', e.target.value)}
          rows={10}
          className="w-full px-3 py-2 rounded-lg text-[11px] font-mono leading-relaxed resize-y outline-none focus:border-[var(--brand-primary)]"
          style={{
            background: 'var(--bg-surface-inset)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-primary)',
            minHeight: '200px',
          }}
          placeholder="Leave empty to use the built-in user prompt for this framework."
        />
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-2">
        <button
          type="button"
          onClick={applyAndSave}
          className="px-4 py-1.5 rounded-lg text-[10px] font-bold text-white cursor-pointer transition-all"
          style={{ background: 'var(--brand-primary)' }}
        >
          Save Overrides
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="px-3 py-1.5 rounded-lg text-[10px] font-bold cursor-pointer transition-all flex items-center gap-1"
          style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}
        >
          <RotateCcw className="w-3 h-3" /> Reset to Defaults
        </button>
      </div>
    </div>
  );
}


const FEATURE_DESCRIPTIONS: Record<string, string> = {
  clinical_instruments: 'PHQ-9, GAD-7, BHS screening tools',
  trait_frameworks: 'Conversation Pattern Analysis, Big Five, Attachment, EI',
  unlimited_patients: 'Manage unlimited patient records',
  report_library: 'Centralized PDF report library with search and export',
  framework_expansion_packs: 'Additional clinical instruments (HCR-20, C-PTSD, Beck scales)',
  cloud_sync: 'Encrypted off-site backup and cross-device sync',
  whatsapp_import: 'Import WhatsApp chat exports',
  audio_upload: 'Upload and transcribe session audio recordings',
};

function SubscriptionSection() {
  const [flags, setFlags] = useState<Record<string, boolean> | null>(null);
  const [tier, setTier] = useState('Free');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    apiFetch<{ tier: string; features: Record<string, boolean> }>('/settings/features')
      .then((data) => { if (mounted) { setTier(data.tier); setFlags(data.features); } })
      .catch(() => {})
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  if (loading) {
    return (
      <Section title="Plan" description="Feature availability and subscription tier.">
        <div className="p-4 text-center text-[11px]" style={{ color: 'var(--text-muted)' }}>Loading...</div>
      </Section>
    );
  }

  const freeFeatures = Object.entries(FEATURE_DESCRIPTIONS).filter(([k]) =>
    ['clinical_instruments', 'trait_frameworks', 'unlimited_patients', 'whatsapp_import', 'audio_upload'].includes(k));
  const proFeatures = Object.entries(FEATURE_DESCRIPTIONS).filter(([k]) =>
    ['report_library', 'framework_expansion_packs', 'cloud_sync'].includes(k));

  return (
    <Section title="Plan" description="Your current tier and feature availability.">
      {/* Current tier badge */}
      <div className="p-4 rounded-lg flex items-center justify-between" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center gap-2">
          {tier === 'Pro' ? (
            <Crown className="w-5 h-5" style={{ color: '#F59E0B' }} />
          ) : (
            <Lock className="w-5 h-5" style={{ color: '#10B981' }} />
          )}
          <div>
            <span className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>{tier} Tier</span>
            <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
              {tier === 'Pro' ? 'All features unlocked' : 'Core features included. Upgrade to unlock Pro.'}
            </p>
          </div>
        </div>
      </div>

      {/* Free features */}
      <div className="space-y-1">
        <h4 className="text-[9px] uppercase font-bold tracking-wider pt-2 pb-1" style={{ color: 'var(--text-muted)' }}>
          Included in Free
        </h4>
        {freeFeatures.map(([key, desc]) => (
          <div key={key} className="flex items-center gap-2 px-3 py-2 rounded-lg text-[10px]" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
            <Check className="w-3 h-3 shrink-0" style={{ color: '#10B981' }} />
            <span style={{ color: 'var(--text-primary)' }}>{desc}</span>
          </div>
        ))}
      </div>

      {/* Pro features */}
      <div className="space-y-1">
        <h4 className="text-[9px] uppercase font-bold tracking-wider pt-3 pb-1" style={{ color: 'var(--text-muted)' }}>
          Pro Features
        </h4>
        {proFeatures.map(([key, desc]) => {
          const enabled = flags?.[key] ?? false;
          return (
            <div key={key} className="flex items-center gap-2 px-3 py-2 rounded-lg text-[10px]" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
              {enabled ? (
                <Check className="w-3 h-3 shrink-0" style={{ color: '#10B981' }} />
              ) : (
                <Lock className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
              )}
              <span style={{ color: enabled ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                {desc}
              </span>
              {!enabled && (
                <span
                  className="ml-auto px-1.5 py-0.5 rounded text-[8px] font-bold"
                  style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#F59E0B' }}
                >
                  Pro
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Upgrade CTA */}
      {tier === 'Free' && (
        <div className="p-4 rounded-lg text-center" style={{ background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.15)' }}>
          <p className="text-[11px] font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
            Upgrade to Pro
          </p>
          <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
            Coming next quarter. Get report library, framework expansion packs, and cloud backup.
          </p>
        </div>
      )}
    </Section>
  );
}
