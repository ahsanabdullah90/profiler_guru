'use client';

import React, { memo, useRef, useState, useEffect } from 'react';
import {
  Cpu, FileText, Download, RefreshCw, Bot, Sparkles, ChevronDown, AlertTriangle,
} from 'lucide-react';
import { apiFetch, type ProfileMeta, type AvailableModel } from '../store/api';
import { useStatusStore } from '../store/statusStore';
import ScoreChart from './ScoreChart';

const FRAMEWORK_DEFS = [
  {
    id: 'communication_style',
    label: 'Conversation Pattern Analysis',
    description: 'Analyze directness, expressiveness, responsiveness, formality, and conflict patterns in conversation.',
    steps: 5,
  },
  {
    id: 'big_five',
    label: 'Big Five / OCEAN',
    description: 'Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism.',
    steps: 5,
  },
  {
    id: 'attachment',
    label: 'Attachment Style',
    description: 'Secure, Anxious, Avoidant, or Disorganized attachment patterns.',
    steps: 6,
  },
  {
    id: 'emotional_intelligence',
    label: 'Emotional Intelligence',
    description: 'Goleman: Self-awareness, Self-regulation, Motivation, Empathy, Social Skills.',
    steps: 8,
  },
];

const LARGE_MODEL_PATTERNS = [
  /^gpt-4/i, /^o1-/i, /^o3-/i, /^claude-3/i, /^claude-sonnet/i, /^claude-opus/i,
  /gemini-(1\.5|2\.0)-(pro|flash)/i, /gemini-(pro|flash)-\d/i,
  /llama3(\.1)?:70b/i, /llama3:405b/i, /mixtral:8x22b/i,
  /qwen2\.5:72b/i, /qwen3:\d+b/i, /gemma2:27b/i,
];

function isSmallModel(modelName: string | undefined | null): boolean {
  if (!modelName) return false;
  return !LARGE_MODEL_PATTERNS.some((p) => p.test(modelName));
}

interface Props {
  selectedContact: string;
  availableMonths: string[];
  startMonth: string;
  endMonth: string;
  setSelectedStartMonth: (v: string | null) => void;
  setSelectedEndMonth: (v: string | null) => void;
  userConsent: boolean;
  setUserConsent: (v: boolean) => void;
  selectedModel: { provider: string; model: string } | null;
  setSelectedModel: (v: { provider: string; model: string } | null) => void;
  frameworkId: string;
  setFrameworkId: (v: string) => void;
  handleGenerateProfile: (e: React.FormEvent) => void;
  savedProfile: string | null;
  isGeneratingProfile: boolean;
  profileMeta: ProfileMeta | null;
  isCompilingPDF: boolean;
  isPDFCompiled: boolean;
  handleCompilePDF: () => void;
  handleDownloadPDF: () => void;
  clearProfile: () => void;
  cancelProfileGeneration: () => void;
}

function AssessmentPanel({
  selectedContact,
  availableMonths,
  startMonth,
  endMonth,
  setSelectedStartMonth,
  setSelectedEndMonth,
  userConsent,
  setUserConsent,
  selectedModel,
  setSelectedModel,
  frameworkId,
  setFrameworkId,
  handleGenerateProfile,
  savedProfile,
  isGeneratingProfile,
  profileMeta,
  isCompilingPDF,
  isPDFCompiled,
  handleCompilePDF,
  handleDownloadPDF,
  clearProfile,
  cancelProfileGeneration,
}: Props) {
  const [models, setModels] = useState<AvailableModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const modelsFetched = useRef(false);

  const cloudModelSelected = selectedModel && models.find(
    (m) => m.provider === selectedModel.provider && m.model === selectedModel.model
  )?.is_cloud;

  const canGenerate = !cloudModelSelected || userConsent;

  useEffect(() => {
    if (modelDropdownOpen && !modelsFetched.current && !modelsLoading) {
      modelsFetched.current = true;
      setModelsLoading(true);
      setModelsError(null);
      apiFetch<{ models: AvailableModel[]; errors: Record<string, string> }>('/models')
        .then((data) => {
          setModels(data.models || []);
          if (data.errors && Object.keys(data.errors).length > 0) {
            const errMsgs = Object.entries(data.errors)
              .map(([p, e]) => `${p}: ${e}`)
              .join('; ');
            setModelsError(errMsgs);
          }
        })
        .catch((err) => {
          setModelsError(err instanceof Error ? err.message : 'Failed to load models');
          modelsFetched.current = false;
        })
        .finally(() => setModelsLoading(false));
    }
  }, [modelDropdownOpen, modelsLoading]);

  const groupedModels = models.reduce<Record<string, AvailableModel[]>>((acc, m) => {
    if (!acc[m.provider]) acc[m.provider] = [];
    acc[m.provider].push(m);
    return acc;
  }, {});

  const renderMarkdown = (text: string): React.ReactNode[] => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let listItems: React.ReactNode[] | null = null;
    let listStyle: 'ul' | 'ol' | null = null;

    const renderLine = (line: string, i: number): React.ReactNode => {
      if (line.startsWith('### ')) return <h3 key={i} className="text-sm font-bold mt-3 mb-1">{renderInline(line.slice(4))}</h3>;
      if (line.startsWith('## ')) return <h2 key={i} className="text-base font-bold mt-3 mb-1">{renderInline(line.slice(3))}</h2>;
      if (line.startsWith('# ')) return <h1 key={i} className="text-lg font-bold mt-4 mb-2">{renderInline(line.slice(2))}</h1>;
      return <p key={i} className="mb-1">{renderInline(line)}</p>;
    };

    const renderInline = (s: string): React.ReactNode => {
      const boldParts = s.split(/(\*\*.*?\*\*)/);
      return boldParts.map((part, j) => {
        if (part.startsWith('**') && part.endsWith('**')) return <strong key={j}>{part.slice(2, -2)}</strong>;
        const italicParts = part.split(/(\*.*?\*)/);
        return italicParts.map((p, k) => {
          if (p.startsWith('*') && p.endsWith('*') && !p.startsWith('**')) return <em key={`${j}-${k}`}>{p.slice(1, -1)}</em>;
          const codeParts = p.split(/(`.*?`)/);
          return codeParts.map((c, l) => {
            if (c.startsWith('`') && c.endsWith('`')) return <code key={`${j}-${k}-${l}`} className="px-1 py-0.5 rounded text-[10px]" style={{ background: 'var(--bg-surface)', fontFamily: 'monospace' }}>{c.slice(1, -1)}</code>;
            return c;
          });
        });
      });
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        if (!listItems) { listItems = []; listStyle = 'ul'; }
        listItems.push(<li key={i} className="ml-4 text-[11px]">{renderInline(trimmed.slice(2))}</li>);
        continue;
      }
      if (/^\d+\.\s/.test(trimmed)) {
        if (!listItems) { listItems = []; listStyle = 'ol'; }
        listItems.push(<li key={i} className="ml-4 text-[11px]">{renderInline(trimmed.replace(/^\d+\.\s/, ''))}</li>);
        continue;
      }

      if (listItems) {
        elements.push(listStyle === 'ol' ? <ol key={`list-${i}`} className="list-decimal pl-2 my-2">{listItems}</ol> : <ul key={`list-${i}`} className="list-disc pl-2 my-2">{listItems}</ul>);
        listItems = null; listStyle = null;
      }

      if (!trimmed) {
        elements.push(<br key={i} />);
      } else {
        elements.push(renderLine(line, i));
      }
    }

    if (listItems) {
      elements.push(listStyle === 'ol' ? <ol key="list-end" className="list-decimal pl-2 my-2">{listItems}</ol> : <ul key="list-end" className="list-disc pl-2 my-2">{listItems}</ul>);
    }

    return elements;
  };

  return (
    <div
      className="h-[65%] border-b flex flex-col overflow-hidden p-5"
      style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-surface-inset)' }}
    >
      {/* Setup Controls */}
      {!savedProfile && !isGeneratingProfile ? (
        <div className="flex-1 flex flex-col justify-center items-center max-w-md mx-auto text-center gap-4">
          <FileText className="w-9 h-9 opacity-85" style={{ color: 'var(--brand-primary)' }} />
          <h3 className="text-sm font-bold text-[var(--text-primary)]">
            Generate Personality Assessment
          </h3>
          <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
            Run a full behavioral scan to generate a psychological assessment report, extracting
            linguistic patterns, emotional sentiment, and personality traits.
          </p>

          <form onSubmit={handleGenerateProfile} className="w-full flex flex-col gap-3 mt-2 text-left">
            {availableMonths.length > 0 ? (
              <div className="grid grid-cols-2 gap-2">
                <div className="flex flex-col gap-1">
                  <label htmlFor="start-month" className="text-[9px] uppercase text-[var(--text-muted)] font-bold">
                    Start Month
                  </label>
                  <select
                    id="start-month"
                    value={startMonth}
                    onChange={(e) => setSelectedStartMonth(e.target.value)}
                    className="px-2 py-1.5 rounded-lg text-[10px] text-[var(--text-primary)] cursor-pointer outline-none focus:border-[var(--brand-primary)]"
                    style={{ background: 'var(--bg-surface-inset)', border: '1px solid var(--border-subtle)' }}
                  >
                    {availableMonths.map((m) => (
                      <option key={m} value={m.replace('.md', '')}>{m.replace('.md', '')}</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label htmlFor="end-month" className="text-[9px] uppercase text-[var(--text-muted)] font-bold">
                    End Month
                  </label>
                  <select
                    id="end-month"
                    value={endMonth}
                    onChange={(e) => setSelectedEndMonth(e.target.value)}
                    className="px-2 py-1.5 rounded-lg text-[10px] text-[var(--text-primary)] cursor-pointer outline-none focus:border-[var(--brand-primary)]"
                    style={{ background: 'var(--bg-surface-inset)', border: '1px solid var(--border-subtle)' }}
                  >
                    {availableMonths.map((m) => (
                      <option key={m} value={m.replace('.md', '')}>{m.replace('.md', '')}</option>
                    ))}
                  </select>
                </div>
              </div>
            ) : null}

            {/* Framework selector */}
            <div className="flex flex-col gap-1">
              <label className="text-[9px] uppercase text-[var(--text-muted)] font-bold">Assessment Type</label>
              <div className="flex flex-wrap gap-1.5">
                {FRAMEWORK_DEFS.map((fw) => (
                  <button
                    key={fw.id}
                    type="button"
                    onClick={() => setFrameworkId(fw.id)}
                    className="flex-1 min-w-[100px] px-2 py-1.5 rounded-lg text-[10px] font-bold text-left transition-all cursor-pointer"
                    style={{
                      background: frameworkId === fw.id ? 'var(--brand-primary)' : 'var(--bg-surface-inset)',
                      border: frameworkId === fw.id
                        ? '1px solid var(--brand-primary)'
                        : '1px solid var(--border-subtle)',
                      color: frameworkId === fw.id ? '#fff' : 'var(--text-secondary)',
                    }}
                  >
                    {fw.label}
                  </button>
                ))}
              </div>
              <p className="text-[9px] text-[var(--text-muted)] italic leading-relaxed">
                {FRAMEWORK_DEFS.find((f) => f.id === frameworkId)?.description}
              </p>
            </div>

            {/* Model picker */}
            <div className="flex flex-col gap-1 relative">
              <label className="text-[9px] uppercase text-[var(--text-muted)] font-bold">Model</label>
              <button
                type="button"
                onClick={() => setModelDropdownOpen((o) => !o)}
                className="px-2 py-1.5 rounded-lg text-[10px] text-left flex items-center justify-between cursor-pointer"
                style={{ background: 'var(--bg-surface-inset)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
              >
                <span>
                  {selectedModel
                    ? `${selectedModel.model} (${selectedModel.provider})`
                    : 'Use default from Settings'}
                </span>
                {modelsLoading ? (
                  <RefreshCw className="w-3 h-3 animate-spin" style={{ color: 'var(--text-muted)' }} />
                ) : (
                  <ChevronDown className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
                )}
              </button>

              {modelDropdownOpen && (
                <div
                  className="absolute top-full left-0 right-0 z-10 mt-1 rounded-lg overflow-y-auto shadow-xl max-h-60"
                  style={{ background: 'var(--bg-surface-raised)', border: '1px solid var(--border-subtle)' }}
                >
                  <button
                    type="button"
                    onClick={() => { setSelectedModel(null); setModelDropdownOpen(false); }}
                    className="w-full text-left px-3 py-2 text-[10px] font-bold hover:opacity-80 cursor-pointer"
                    style={{ color: 'var(--text-primary-de)', borderBottom: '1px solid var(--border-subtle)', background: 'transparent' }}
                  >
                    Use default from Settings
                  </button>
                  {Object.entries(groupedModels).map(([provider, providerModels]) => (
                    <div key={provider}>
                      <div
                        className="px-3 py-1.5 text-[8px] uppercase font-bold tracking-wider"
                        style={{ color: 'var(--text-muted)', background: 'var(--bg-surface)' }}
                      >
                        {provider}
                      </div>
                      {providerModels.map((m) => (
                        <button
                          key={`${m.provider}:${m.model}`}
                          type="button"
                          onClick={() => { setSelectedModel({ provider: m.provider, model: m.model }); setModelDropdownOpen(false); }}
                          className="w-full text-left px-3 py-1.5 text-[10px] flex items-center justify-between cursor-pointer hover:opacity-80"
                          style={{
                            color: 'var(--text-secondary)',
                            background: selectedModel?.provider === m.provider && selectedModel?.model === m.model
                              ? 'var(--brand-primary-soft)' : 'transparent',
                          }}
                        >
                          <span>{m.model}</span>
                          {m.is_cloud ? (
                            <span className="text-[8px] px-1 py-0.5 rounded" style={{ background: 'rgba(255, 170, 0, 0.15)', color: 'var(--warning)' }}>
                              cloud
                            </span>
                          ) : null}
                        </button>
                      ))}
                    </div>
                  ))}
                  {models.length === 0 && !modelsLoading ? (
                    <div className="px-3 py-3 text-[10px] italic text-center" style={{ color: 'var(--text-muted)' }}>
                      {modelsError || 'No models found. Is Ollama running?'}
                    </div>
                  ) : null}
                </div>
              )}
            </div>

            {/* Cloud warning + consent */}
            {cloudModelSelected && !userConsent ? (
              <div
                className="flex items-center gap-2 p-2.5 rounded-lg text-[10px]"
                style={{ background: 'rgba(255, 170, 0, 0.1)', border: '1px solid var(--warning)', color: 'var(--warning)' }}
              >
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>This model routes chat logs to a cloud API. Check consent below to enable.</span>
              </div>
            ) : null}

            <div
              className="flex items-center justify-between p-3 rounded-lg text-[10px] mt-1"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}
            >
              <span className="flex items-center gap-1.5 font-bold" style={{ color: cloudModelSelected ? 'var(--warning)' : 'var(--text-secondary)' }}>
                <Cpu className="w-3.5 h-3.5" />
                {cloudModelSelected ? 'Cloud model selected — consent required' : 'No cloud consent needed'}
              </span>
              <input
                type="checkbox"
                checked={userConsent}
                onChange={(e) => setUserConsent(e.target.checked)}
                style={{ accentColor: 'var(--warning)' }}
                aria-label="Cloud processing consent"
              />
            </div>

            <button
              type="submit"
              disabled={!canGenerate}
              className="w-full py-2 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-2 mt-2 cursor-pointer text-white disabled:opacity-40"
              style={{ background: 'var(--brand-primary)' }}
            >
              <Sparkles className="w-3.5 h-3.5" /> Generate Psychological Profile
            </button>
          </form>
        </div>
      ) : null}

      {/* Generating spinner with cancel */}
      {isGeneratingProfile ? (
        <div className="flex-1 flex flex-col justify-center items-center gap-3.5">
          <RefreshCw className="w-8 h-8 animate-spin" style={{ color: 'var(--brand-primary)' }} />
          <p className="text-xs font-bold text-[var(--text-primary)]">
            {isSmallModel(selectedModel?.model)
              ? `Running ${FRAMEWORK_DEFS.find((f) => f.id === frameworkId)?.steps || 5}-step analysis for ${selectedContact}…`
              : `Analyzing conversation logs for ${selectedContact}…`}
          </p>
          <p className="text-[10px] text-[var(--text-muted)]">
            {isSmallModel(selectedModel?.model)
              ? 'Sequential multi-step analysis. Each step focuses on one dimension for better accuracy with this model.'
              : 'Retrieving vectors, indexing patterns, and dispatching to LLM.'}
          </p>
          <button
            type="button"
            onClick={cancelProfileGeneration}
            className="px-3 py-1.5 rounded-lg text-[10px] font-bold cursor-pointer transition-all hover:opacity-80"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}
          >
            Cancel
          </button>
        </div>
      ) : null}

      {/* Assessment results */}
      {savedProfile && !isGeneratingProfile ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between pb-2 mb-3 shrink-0" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <div className="flex flex-col">
              <h3 className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                <Bot className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} /> Personality Profile Assessment
              </h3>
              <span className="text-[10px] text-[var(--text-muted)] mt-0.5">
                {FRAMEWORK_DEFS.find((f) => f.id === profileMeta?.framework_id)?.label || 'Assessment'}
                {' | '}Range: {profileMeta?.start_month?.replace('.md', '')} to {profileMeta?.end_month?.replace('.md', '')}
                {' | '}Engine: {profileMeta?.model}
                {profileMeta?.generated_at ? ` | ${new Date(profileMeta.generated_at).toLocaleString()}` : ''}
              </span>
            </div>
            <div className="flex gap-2">
              {isPDFCompiled ? (
                <button type="button" onClick={handleDownloadPDF} className="px-3 py-1 font-bold text-[10px] rounded-md flex items-center gap-1 transition-all cursor-pointer text-black" style={{ background: 'var(--success)' }} aria-label="Download PDF report">
                  <Download className="w-3.5 h-3.5" /> Download PDF
                </button>
              ) : (
                <button type="button" onClick={handleCompilePDF} disabled={isCompilingPDF} className="px-3 py-1 font-bold text-[10px] rounded-md flex items-center gap-1 transition-all cursor-pointer text-white disabled:opacity-40" style={{ background: 'var(--brand-primary)' }} aria-label="Compile PDF report">
                  {isCompilingPDF ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                  Compile Report PDF
                </button>
              )}
              <button type="button" onClick={clearProfile} className="px-2.5 py-1 rounded-md font-bold text-[10px] transition-all cursor-pointer" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }} aria-label="Regenerate profile">
                Regenerate
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto pr-1 space-y-3 font-sans text-xs leading-relaxed select-text" style={{ color: 'var(--text-primary)', scrollbarWidth: 'thin' }}>
            {profileMeta?.scores && Object.keys(profileMeta.scores).length > 0 ? (
              <ScoreChart
                scores={profileMeta.scores}
                frameworkId={profileMeta.framework_id || 'communication_style'}
                classification={profileMeta.classification}
              />
            ) : null}
            <div className="prose prose-invert max-w-none prose-xs">
              {renderMarkdown(savedProfile)}
            </div>
            <div className="p-3 mt-5 rounded-lg text-[10px] italic text-center leading-normal" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
              ⚠️ <b>Disclaimer:</b> This report is AI-generated analysis based on text communication patterns. It is not a clinical or diagnostic assessment.
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default memo(AssessmentPanel);
