'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRagStore } from '../store/ragStore';
import { useContactsStore } from '../store/contactsStore';
import { useStatusStore } from '../store/statusStore';
import { getApiBase, apiFetch, ApiError } from '../store/api';
import { useDebouncedCallback } from '../lib/useDebounce';
import { ArrowLeft, Search, Sparkles } from 'lucide-react';
import AIHubAssessment from './AIHubAssessment';
import AIHubRAGChat from './AIHubRAGChat';

export default function AIHub() {
  const selectedContact = useContactsStore((s) => s.selectedContact);
  const setSelectedContact = useContactsStore((s) => s.setSelectedContact);
  const availableMonths = useContactsStore((s) => s.availableMonths);
  const savedProfile = useRagStore((s) => s.savedProfile);
  const profileMeta = useRagStore((s) => s.profileMeta);
  const isGeneratingProfile = useRagStore((s) => s.isGeneratingProfile);
  const isQueryingRAG = useRagStore((s) => s.isQueryingRAG);
  const ragChatHistory = useRagStore((s) => s.ragChatHistory);
  const globalSearchQuery = useRagStore((s) => s.globalSearchQuery);
  const globalSearchResults = useRagStore((s) => s.globalSearchResults);
  const generateProfile = useRagStore((s) => s.generateProfile);
  const queryRAG = useRagStore((s) => s.queryRAG);
  const globalSearch = useRagStore((s) => s.globalSearch);
  const clearProfile = useRagStore((s) => s.clearProfile);
  const setGlobalSearchQuery = useRagStore((s) => s.setGlobalSearchQuery);

  const [selectedStartMonth, setSelectedStartMonth] = useState<string | null>(null);
  const [selectedEndMonth, setSelectedEndMonth] = useState<string | null>(null);
  const [deepScan, setDeepScan] = useState(false);
  const [forceCloud, setForceCloud] = useState(false);
  const [userConsent, setUserConsent] = useState(false);
  const [ragQuery, setRagQuery] = useState('');
  const [isCompilingPDF, setIsCompilingPDF] = useState(false);
  const [isPDFCompiled, setIsPDFCompiled] = useState(false);

  const pdfPollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevContactRef = useRef<string | null>(null);

  useEffect(() => {
    if (selectedContact !== prevContactRef.current) {
      prevContactRef.current = selectedContact;
      setSelectedStartMonth(null);
      setSelectedEndMonth(null);
    }
  }, [selectedContact]);

  useEffect(() => {
    return () => {
      if (pdfPollRef.current) {
        clearTimeout(pdfPollRef.current);
        pdfPollRef.current = null;
      }
    };
  }, []);

  const startMonth = selectedStartMonth ?? (availableMonths.length > 0 ? availableMonths[availableMonths.length - 1] : '');
  const endMonth = selectedEndMonth ?? (availableMonths.length > 0 ? availableMonths[0] : '');

  const handleGenerateProfile = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedContact || !startMonth || !endMonth) return;
    generateProfile(selectedContact, startMonth, endMonth, forceCloud, deepScan, userConsent);
  };

  const handleRAGQuerySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedContact || !ragQuery.trim()) return;
    queryRAG(selectedContact, ragQuery, startMonth || null, endMonth || null, deepScan, userConsent);
    setRagQuery('');
  };

  const handleRetryRAG = (err: { query: string; start_month: string | null; end_month: string | null; deep_scan: boolean; user_consent: boolean }) => {
    if (selectedContact) {
      queryRAG(selectedContact, err.query, err.start_month, err.end_month, err.deep_scan, err.user_consent);
    }
  };

  const handleGlobalSearch = useDebouncedCallback((value: string) => {
    setGlobalSearchQuery(value);
    globalSearch(value);
  }, 300);

  const handleCompilePDF = async () => {
    if (!selectedContact || !savedProfile || !profileMeta) return;
    setIsCompilingPDF(true);
    setIsPDFCompiled(false);

    try {
      await apiFetch(`/reports/contacts/${selectedContact}/generate`, {
        method: 'POST',
        body: JSON.stringify({ start_month: profileMeta.start_month, end_month: profileMeta.end_month, profile_text: savedProfile }),
      });
      const pollInterval = 1500;
      const maxAttempts = 40;
      let attempts = 0;
      const pollStatus = async () => {
        try {
          const statusRes = await apiFetch<{ status: string; error?: string }>(`/reports/contacts/${selectedContact}/generate/status`);
          if (statusRes.status === 'completed') { setIsPDFCompiled(true); setIsCompilingPDF(false); }
          else if (statusRes.status === 'failed') { useStatusStore.getState().pushError(`PDF compilation failed: ${statusRes.error || 'Unknown error'}`, 'error'); setIsCompilingPDF(false); }
          else { attempts++; if (attempts < maxAttempts) { pdfPollRef.current = setTimeout(pollStatus, pollInterval); } else { useStatusStore.getState().pushError('PDF compilation timed out.', 'error'); setIsCompilingPDF(false); } }
        } catch (pollErr: unknown) { useStatusStore.getState().pushError(`Error checking report status: ${pollErr instanceof Error ? pollErr.message : 'Unknown error'}`, 'error'); setIsCompilingPDF(false); }
      };
      pdfPollRef.current = setTimeout(pollStatus, pollInterval);
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : 'Unknown error';
      useStatusStore.getState().pushError(e instanceof ApiError ? `Failed to trigger report compilation: ${errMsg}` : `PDF compilation failed: ${errMsg}`, 'error');
      setIsCompilingPDF(false);
    }
  };

  const handleDownloadPDF = () => {
    if (!selectedContact) return;
    window.open(`${getApiBase()}/reports/contacts/${selectedContact}/download`, '_blank');
  };

  return (
    <div className="w-full h-full flex flex-col overflow-hidden">
      {!selectedContact ? (
        <div className="flex-1 p-6 flex flex-col justify-center items-center overflow-hidden relative">
          <div className="w-full max-w-xl flex flex-col gap-5 text-center">
            <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto shadow-lg" style={{ background: 'var(--brand-primary-soft)', border: '1px solid var(--brand-primary)', boxShadow: '0 0 24px var(--brand-primary-glow)' }}>
              <Sparkles className="w-5 h-5" style={{ color: 'var(--brand-primary)' }} />
            </div>
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-[var(--text-primary)]">Global Intelligence Search</h2>
              <p className="text-xs text-[var(--text-muted)] max-w-md mx-auto leading-relaxed">
                Execute semantic search queries across all indexed chats and transcription logs instantly utilizing local vector embeddings.
              </p>
            </div>
            <div className="relative mt-2">
              <Search className="w-4 h-4 absolute left-4 top-3" style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
              <input type="text" value={globalSearchQuery} onChange={(e) => handleGlobalSearch(e.target.value)} placeholder="Ask anything (e.g., Who discussed meeting next week?)..." className="w-full pl-11 pr-4 py-2.5 rounded-xl text-xs outline-none transition-all" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }} aria-label="Global semantic search" />
            </div>
            {globalSearchResults.length > 0 ? (
              <div className="mt-4 flex-1 text-left overflow-y-auto max-h-[300px] space-y-2 pr-1" style={{ scrollbarWidth: 'thin' }}>
                {globalSearchResults.map((match) => (
                  <div key={match.id} className="p-3 rounded-lg flex flex-col gap-2" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)' }}>
                    <div className="flex justify-between items-center text-[10px] font-bold">
                      <span style={{ color: 'var(--data-1)' }}>@{match.chat_name}</span>
                      <span className="font-mono" style={{ color: 'var(--text-muted)' }}>{match.month}</span>
                    </div>
                    <p className="text-[11px] leading-relaxed italic" style={{ color: 'var(--text-secondary)' }}>&quot;{match.document}&quot;</p>
                  </div>
                ))}
              </div>
            ) : globalSearchQuery.trim() ? (
              <div className="text-xs italic mt-4" style={{ color: 'var(--text-muted)' }}>No matching semantic blocks found.</div>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden relative">
          <div className="p-3 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] shrink-0 flex items-center">
            <button onClick={() => setSelectedContact(null)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-primary/30 bg-primary/15 text-xs font-bold text-white hover:bg-primary/25 hover:border-primary/50 transition-all cursor-pointer">
              <ArrowLeft className="w-3.5 h-3.5" /> Back
            </button>
          </div>
          <AIHubAssessment
            selectedContact={selectedContact}
            availableMonths={availableMonths}
            startMonth={startMonth}
            endMonth={endMonth}
            setSelectedStartMonth={setSelectedStartMonth}
            setSelectedEndMonth={setSelectedEndMonth}
            deepScan={deepScan}
            forceCloud={forceCloud}
            userConsent={userConsent}
            setDeepScan={setDeepScan}
            setForceCloud={setForceCloud}
            setUserConsent={setUserConsent}
            handleGenerateProfile={handleGenerateProfile}
            savedProfile={savedProfile}
            isGeneratingProfile={isGeneratingProfile}
            profileMeta={profileMeta}
            isCompilingPDF={isCompilingPDF}
            isPDFCompiled={isPDFCompiled}
            handleCompilePDF={handleCompilePDF}
            handleDownloadPDF={handleDownloadPDF}
            clearProfile={clearProfile}
          />
          <AIHubRAGChat
            selectedContact={selectedContact}
            ragChatHistory={ragChatHistory}
            isQueryingRAG={isQueryingRAG}
            ragQuery={ragQuery}
            setRagQuery={setRagQuery}
            handleRAGQuerySubmit={handleRAGQuerySubmit}
            onRetryError={handleRetryRAG}
          />
        </div>
      )}
    </div>
  );
}
