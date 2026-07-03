'use client';

import React, { memo } from 'react';
import {
  Cpu, FileText, Download, RefreshCw, Bot, Sparkles,
} from 'lucide-react';

interface ProfileMeta {
  start_month: string;
  end_month: string;
  model: string;
}

interface Props {
  selectedContact: string;
  availableMonths: string[];
  startMonth: string;
  endMonth: string;
  setSelectedStartMonth: (v: string | null) => void;
  setSelectedEndMonth: (v: string | null) => void;
  deepScan: boolean;
  forceCloud: boolean;
  userConsent: boolean;
  setDeepScan: (v: boolean) => void;
  setForceCloud: (v: boolean) => void;
  setUserConsent: (v: boolean) => void;
  handleGenerateProfile: (e: React.FormEvent) => void;
  savedProfile: string | null;
  isGeneratingProfile: boolean;
  profileMeta: ProfileMeta | null;
  isCompilingPDF: boolean;
  isPDFCompiled: boolean;
  handleCompilePDF: () => void;
  handleDownloadPDF: () => void;
  clearProfile: () => void;
}

function AssessmentPanel({
  selectedContact,
  availableMonths,
  startMonth,
  endMonth,
  setSelectedStartMonth,
  setSelectedEndMonth,
  deepScan,
  forceCloud,
  userConsent,
  setDeepScan,
  setForceCloud,
  setUserConsent,
  handleGenerateProfile,
  savedProfile,
  isGeneratingProfile,
  profileMeta,
  isCompilingPDF,
  isPDFCompiled,
  handleCompilePDF,
  handleDownloadPDF,
  clearProfile,
}: Props) {
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
                  {/* eslint-disable-next-line jsx-a11y/no-onchange -- <select> requires onChange */}
                  <select
                    id="start-month"
                    value={startMonth}
                    onChange={(e) => setSelectedStartMonth(e.target.value)}
                    className="px-2 py-1.5 rounded-lg text-[10px] text-[var(--text-primary)] cursor-pointer outline-none focus:border-[var(--brand-primary)]"
                    style={{ background: 'var(--bg-surface-inset)', border: '1px solid var(--border-subtle)' }}
                  >
                    {availableMonths.map((m) => (
                      <option key={m} value={m}>{m.replace('.md', '')}</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label htmlFor="end-month" className="text-[9px] uppercase text-[var(--text-muted)] font-bold">
                    End Month
                  </label>
                  {/* eslint-disable-next-line jsx-a11y/no-onchange -- <select> requires onChange */}
                  <select
                    id="end-month"
                    value={endMonth}
                    onChange={(e) => setSelectedEndMonth(e.target.value)}
                    className="px-2 py-1.5 rounded-lg text-[10px] text-[var(--text-primary)] cursor-pointer outline-none focus:border-[var(--brand-primary)]"
                    style={{ background: 'var(--bg-surface-inset)', border: '1px solid var(--border-subtle)' }}
                  >
                    {availableMonths.map((m) => (
                      <option key={m} value={m}>{m.replace('.md', '')}</option>
                    ))}
                  </select>
                </div>
              </div>
            ) : null}

            <fieldset
              className="flex flex-col gap-2 p-3 rounded-lg mt-1"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}
            >
              <legend className="text-[9px] uppercase text-[var(--text-muted)] font-bold flex items-center gap-1 px-1">
                <Cpu className="w-3.5 h-3.5" /> AI Engine Router
              </legend>
              <div className="flex items-center justify-between text-[10px] mt-1">
                <span className="text-[var(--text-secondary)]">Force Cloud (Gemini)</span>
                <input
                  type="checkbox"
                  checked={forceCloud}
                  onChange={(e) => setForceCloud(e.target.checked)}
                  style={{ accentColor: 'var(--brand-primary)' }}
                  aria-label="Force Cloud (Gemini)"
                />
              </div>
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-[var(--text-secondary)]">Thorough Deep Scan</span>
                <input
                  type="checkbox"
                  checked={deepScan}
                  onChange={(e) => setDeepScan(e.target.checked)}
                  style={{ accentColor: 'var(--brand-primary)' }}
                  aria-label="Thorough Deep Scan"
                />
              </div>
              <div className="flex items-center justify-between text-[10px] pt-1.5 mt-1" style={{ borderTop: '1px solid var(--border-subtle)' }}>
                <span className="font-bold" style={{ color: 'var(--warning)' }}>Cloud processing consent</span>
                <input
                  type="checkbox"
                  checked={userConsent}
                  onChange={(e) => setUserConsent(e.target.checked)}
                  style={{ accentColor: 'var(--warning)' }}
                  aria-label="Cloud processing consent"
                />
              </div>
            </fieldset>

            <button
              type="submit"
              className="w-full py-2 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-2 mt-2 cursor-pointer text-white"
              style={{ background: 'var(--brand-primary)' }}
            >
              <Sparkles className="w-3.5 h-3.5" /> Generate Psychological Profile
            </button>
          </form>
        </div>
      ) : null}

      {/* Generating spinner */}
      {isGeneratingProfile ? (
        <div className="flex-1 flex flex-col justify-center items-center gap-3.5">
          <RefreshCw className="w-8 h-8 animate-spin" style={{ color: 'var(--brand-primary)' }} />
          <p className="text-xs font-bold text-[var(--text-primary)]">
            Analyzing conversation logs for {selectedContact}…
          </p>
          <p className="text-[10px] text-[var(--text-muted)]">
            Retrieving vectors, indexing patterns, and dispatching to LLM.
          </p>
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
                Range: {profileMeta?.start_month?.replace('.md', '')} to {profileMeta?.end_month?.replace('.md', '')} | Engine: {profileMeta?.model}
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
            <div className="prose prose-invert max-w-none prose-xs">
              <div className="whitespace-pre-wrap font-sans">{savedProfile}</div>
            </div>
            <div className="p-3 mt-5 rounded-lg text-[10px] italic text-center leading-normal" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
              ⚠️ <b>Disclaimer:</b> The &quot;psychological profile&quot; is AI-generated analysis, not clinical psychology. This protects against liability.
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default memo(AssessmentPanel);
