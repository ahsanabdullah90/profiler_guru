'use client';

/**
 * Settings panel — token-driven, grouped (Data / Models / About).
 * Fetches /api/v1/settings on mount and persists changes via POST.
 */

import React, { useEffect, useState } from 'react';
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
} from 'lucide-react';

interface SettingsData {
  cloud_provider: string;
  cloud_api_key: string;
  llm_provider: string;
  ollama_model: string;
  deep_scan_default: boolean;
  pdf_include_charts: boolean;
  pdf_include_raw_snippets: boolean;
  pdf_include_textual_profile: boolean;
  report_sections_order: string[];
  rag_relevancy_threshold: number;
  rag_token_budget_ollama: number;
  rag_token_budget_gemini: number;
  assessment_min_blocks: number;
}

interface SettingsResponse {
  settings: SettingsData;
  installed_ollama_models: string[];
  best_local_model: string | null;
}

type Group = 'data' | 'models' | 'about';

export default function SettingsPanel() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [activeGroup, setActiveGroup] = useState<Group>('data');
  const theme = useUIStore((s) => s.theme);

  useEffect(() => {
    let mounted = true;
    apiFetch('/settings')
      .then((res: unknown) => {
        if (!mounted) return;
        setData(res as SettingsResponse);
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

  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    setMessage(null);
    try {
      await apiFetch('/settings', {
        method: 'POST',
        body: JSON.stringify({ settings: data.settings }),
      });
      setMessage({ type: 'success', text: 'Settings saved' });
      setTimeout(() => setMessage(null), 3000);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setMessage({ type: 'error', text: `Save failed: ${msg}` });
    } finally {
      setSaving(false);
    }
  };

  const update = <K extends keyof SettingsData>(key: K, value: SettingsData[K]) => {
    if (!data) return;
    setData({ ...data, settings: { ...data.settings, [key]: value } });
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
      <header className="h-[56px] px-6 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <SettingsIcon className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
          <h2 className="text-sm font-bold text-[var(--text-primary)]">Settings</h2>
        </div>
        <Button onClick={handleSave} loading={saving} variant="primary" size="sm">
          <Save className="w-3.5 h-3.5" />
          Save
        </Button>
      </header>

      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Group nav */}
        <nav
          aria-label="Settings sections"
          className="w-[200px] border-r border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 shrink-0"
        >
          <GroupButton
            icon={<Database className="w-3.5 h-3.5" />}
            label="Data"
            active={activeGroup === 'data'}
            onClick={() => setActiveGroup('data')}
          />
          <GroupButton
            icon={<Cpu className="w-3.5 h-3.5" />}
            label="Models"
            active={activeGroup === 'models'}
            onClick={() => setActiveGroup('models')}
          />
          <GroupButton
            icon={<FileText className="w-3.5 h-3.5" />}
            label="Reports"
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

          {activeGroup === 'data' ? (
            <Section title="Data" description="Where your data lives and how it's processed.">
              <Field label="Cloud Provider">
                <input
                  id="cloud-provider"
                  value={settings.cloud_provider}
                  onChange={(e) => update('cloud_provider', e.target.value)}
                  className="w-full h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)]"
                />
              </Field>
              <Field
                label="Cloud API Key"
                description="Stored locally in OS keyring. Never sent to remote servers except the cloud provider."
              >
                <input
                  id="cloud-api-key"
                  type="password"
                  value={settings.cloud_api_key}
                  onChange={(e) => update('cloud_api_key', e.target.value)}
                  placeholder="Enter API key"
                  className="w-full h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--brand-primary)] font-mono"
                />
              </Field>
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
            </Section>
          ) : null}

          {activeGroup === 'models' ? (
            <Section title="Models" description="Configure which AI engine generates profiles and answers.">
              <Field label="LLM Provider">
                {/* eslint-disable-next-line jsx-a11y/no-onchange -- <select> requires onChange */}
                <select
                  id="llm-provider"
                  value={settings.llm_provider || settings.cloud_provider}
                  onChange={(e) => update('llm_provider', e.target.value)}
                  className="w-full h-9 px-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)]"
                >
                  <option value="gemini">Google Gemini (Cloud)</option>
                  <option value="ollama">Ollama (Local)</option>
                </select>
              </Field>
              <Field
                label="Ollama Model"
                description={
                  installed_ollama_models.length
                    ? `Installed: ${installed_ollama_models.join(', ')}`
                    : 'No Ollama models installed. Run `ollama pull llama3` to start.'
                }
              >
                <input
                  id="ollama-model"
                  value={settings.ollama_model}
                  onChange={(e) => update('ollama_model', e.target.value)}
                  placeholder="llama3"
                  className="w-full h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--brand-primary)] font-mono"
                />
                {best_local_model ? (
                  <p className="text-[10px] text-[var(--text-muted)] mt-1">
                    Recommended:{' '}
                    <button
                      type="button"
                      onClick={() => update('ollama_model', best_local_model)}
                      className="font-mono font-semibold hover:underline"
                      style={{ color: 'var(--brand-primary)' }}
                    >
                      {best_local_model}
                    </button>
                  </p>
                ) : null}
              </Field>

              <div className="pt-4 mt-4 border-t border-[var(--border-subtle)]">
                <h4 className="text-xs font-bold text-[var(--text-primary)] mb-3">RAG Pipeline Parameters</h4>
                <div className="space-y-4">
                  <Field
                    label="RAG Relevancy Threshold"
                    description="Similarity score threshold (0.0 to 1.0) below which vector chunks are excluded from prompt context. Lower values include more context but increase noise."
                  >
                    <div className="flex items-center gap-3">
                      <input
                        id="rag-relevancy-threshold-slider"
                        type="range"
                        min="0"
                        max="1.0"
                        step="0.05"
                        value={settings.rag_relevancy_threshold ?? 0.3}
                        onChange={(e) => update('rag_relevancy_threshold', parseFloat(e.target.value))}
                        className="w-2/3 h-1.5 rounded-lg appearance-none cursor-pointer bg-[var(--bg-surface-inset)] accent-[var(--brand-primary)]"
                      />
                      <span className="text-xs font-mono font-bold w-12 text-center py-1 rounded bg-[var(--bg-surface-raised)] border border-[var(--border-subtle)]">
                        {settings.rag_relevancy_threshold ?? 0.3}
                      </span>
                    </div>
                  </Field>
                  <Field
                    label="Local Ollama Context Budget (Characters)"
                    description="Maximum character length of assembled context text sent to local Ollama queries (to prevent local model context overflow)."
                  >
                    <input
                      id="rag-token-budget-ollama"
                      type="number"
                      min="1000"
                      max="100000"
                      step="1000"
                      value={settings.rag_token_budget_ollama ?? 15000}
                      onChange={(e) => update('rag_token_budget_ollama', parseInt(e.target.value) || 15000)}
                      className="w-full h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)] font-mono"
                    />
                  </Field>
                  <Field
                    label="Cloud Gemini Context Budget (Characters)"
                    description="Maximum character length of assembled context text sent to Cloud Gemini queries (supports very large context windows)."
                  >
                    <input
                      id="rag-token-budget-gemini"
                      type="number"
                      min="5000"
                      max="1000000"
                      step="5000"
                      value={settings.rag_token_budget_gemini ?? 300000}
                      onChange={(e) => update('rag_token_budget_gemini', parseInt(e.target.value) || 300000)}
                      className="w-full h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)] font-mono"
                    />
                  </Field>
                  <Field
                    label="Minimum Assessment Chat Volume (Message Blocks)"
                    description="Minimum conversational message blocks required to generate a Psychological Profile. Prevents thin reports from low-volume histories."
                  >
                    <input
                      id="assessment-min-blocks"
                      type="number"
                      min="1"
                      max="100"
                      step="1"
                      value={settings.assessment_min_blocks ?? 5}
                      onChange={(e) => update('assessment_min_blocks', parseInt(e.target.value) || 5)}
                      className="w-full h-9 px-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-md text-xs text-[var(--text-primary)] outline-none focus:border-[var(--brand-primary)] font-mono"
                    />
                  </Field>
                </div>
              </div>
            </Section>
          ) : null}

          {activeGroup === 'about' ? (
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

              <div className="pt-4 mt-4 border-t border-[var(--border-subtle)]">
                <h3 className="text-xs font-bold text-[var(--text-primary)] mb-2 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5" style={{ color: 'var(--brand-primary)' }} />
                  About Profile Guru
                </h3>
                <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                  Theme: <span className="font-mono font-semibold">{theme}</span>. All data stays on this machine unless you opt-in to cloud processing per query.
                </p>
              </div>
            </Section>
          ) : null}
        </div>
      </div>
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
