'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRagStore } from '../store/ragStore';
import { useContactsStore } from '../store/contactsStore';
import { getApiBase, apiFetch, ApiError } from '../store/api';
import { useDebouncedCallback } from '../lib/useDebounce';
import { 
  Cpu, Send, FileText, Download, ArrowLeft,
  Search, RefreshCw, MessageSquare, Bot, Sparkles, User
} from 'lucide-react';

export default function AIHub() {
  const selectedContact = useContactsStore(s => s.selectedContact);
  const setSelectedContact = useContactsStore(s => s.setSelectedContact);
  const availableMonths = useContactsStore(s => s.availableMonths);
  const savedProfile = useRagStore(s => s.savedProfile);
  const profileMeta = useRagStore(s => s.profileMeta);
  const isGeneratingProfile = useRagStore(s => s.isGeneratingProfile);
  const isQueryingRAG = useRagStore(s => s.isQueryingRAG);
  const ragChatHistory = useRagStore(s => s.ragChatHistory);
  const globalSearchQuery = useRagStore(s => s.globalSearchQuery);
  const globalSearchResults = useRagStore(s => s.globalSearchResults);
  const generateProfile = useRagStore(s => s.generateProfile);
  const queryRAG = useRagStore(s => s.queryRAG);
  const globalSearch = useRagStore(s => s.globalSearch);
  const clearProfile = useRagStore(s => s.clearProfile);
  const setGlobalSearchQuery = useRagStore(s => s.setGlobalSearchQuery);

  const [selectedStartMonth, setSelectedStartMonth] = useState<string | null>(null);
  const [selectedEndMonth, setSelectedEndMonth] = useState<string | null>(null);
  const [deepScan, setDeepScan] = useState(false);
  const [forceCloud, setForceCloud] = useState(false);
  const [userConsent, setUserConsent] = useState(false);
  const [ragQuery, setRagQuery] = useState('');
  const [isCompilingPDF, setIsCompilingPDF] = useState(false);
  const [isPDFCompiled, setIsPDFCompiled] = useState(false);
  
  const threadEndRef = useRef<HTMLDivElement>(null);
  const pdfPollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevContactRef = useRef<string | null>(null);

  // Reset month selection when contact changes (via useEffect, not render-phase)
  useEffect(() => {
    if (selectedContact !== prevContactRef.current) {
      prevContactRef.current = selectedContact;
      setSelectedStartMonth(null);
      setSelectedEndMonth(null);
    }
  }, [selectedContact]);

  // Cleanup PDF polling on unmount
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

  // Scroll RAG chat thread to bottom on message updates
  useEffect(() => {
    if (threadEndRef.current) {
      threadEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [ragChatHistory]);

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
        body: JSON.stringify({
          start_month: profileMeta.start_month,
          end_month: profileMeta.end_month,
          profile_text: savedProfile
        })
      });
      
      const pollInterval = 1500;
      const maxAttempts = 40;
      let attempts = 0;
      
      const pollStatus = async () => {
        try {
          const statusRes = await apiFetch<{ status: string, error?: string }>(
            `/reports/contacts/${selectedContact}/generate/status`
          );
          
          if (statusRes.status === 'completed') {
            setIsPDFCompiled(true);
            setIsCompilingPDF(false);
          } else if (statusRes.status === 'failed') {
            alert(`PDF compilation failed in background: ${statusRes.error || 'Unknown error'}`);
            setIsCompilingPDF(false);
          } else {
            attempts++;
            if (attempts < maxAttempts) {
              pdfPollRef.current = setTimeout(pollStatus, pollInterval);
            } else {
              alert('PDF compilation timed out. Please try again.');
              setIsCompilingPDF(false);
            }
          }
        } catch (pollErr: unknown) {
          const errMsg = pollErr instanceof Error ? pollErr.message : 'Unknown error';
          alert(`Error checking report status: ${errMsg}`);
          setIsCompilingPDF(false);
        }
      };
      
      pdfPollRef.current = setTimeout(pollStatus, pollInterval);
      
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : 'Unknown error';
      if (e instanceof ApiError) {
        alert(`Failed to trigger report compilation: ${errMsg}`);
      } else {
        alert(`PDF compilation failed: ${errMsg}`);
      }
      setIsCompilingPDF(false);
    }
  };

  const handleDownloadPDF = () => {
    if (!selectedContact) return;
    const url = `${getApiBase()}/reports/contacts/${selectedContact}/download`;
    window.open(url, '_blank');
  };

  return (
    <div className="w-full h-full flex flex-col overflow-hidden">
      
      {/* ==================== STATE A: NO CONTACT LOADED (GLOBAL SEARCH HUB) ==================== */}
      {!selectedContact ? (
        <div className="flex-1 p-6 flex flex-col justify-center items-center overflow-hidden relative">
          
          <div className="w-full max-w-xl flex flex-col gap-5 text-center">
            <div className="w-12 h-12 rounded-full bg-[rgba(121,99,255,0.06)] border border-[rgba(121,99,255,0.15)] flex items-center justify-center mx-auto shadow-lg shadow-[rgba(121,99,255,0.1)]">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
            
            <div className="space-y-2">
              <h2 className="font-outfit font-bold text-xl text-white">Global Intelligence Search</h2>
              <p className="text-xs text-zinc-500 max-w-md mx-auto leading-relaxed">
                Execute semantic search queries across all indexed chats and transcription logs instantly utilizing local vector embeddings.
              </p>
            </div>

            {/* Global Search Input */}
            <div className="relative mt-2">
              <Search className="w-4 h-4 text-zinc-500 absolute left-4 top-3" />
              <input 
                type="text"
                value={globalSearchQuery}
                onChange={(e) => handleGlobalSearch(e.target.value)}
                placeholder="Ask anything (e.g., Who discussed meeting next week?)..."
                className="w-full pl-11 pr-4 py-2.5 bg-[rgba(255,255,255,0.015)] border border-[var(--border-glass)] rounded-xl text-xs text-white outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all"
              />
            </div>

            {/* Semantic Search results list */}
            {globalSearchResults.length > 0 ? (
              <div className="mt-4 flex-1 text-left overflow-y-auto max-h-[300px] space-y-2 pr-1 scrollbar-thin scrollbar-thumb-zinc-800">
                {globalSearchResults.map((match) => (
                  <div 
                    key={match.id}
                    className="p-3 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg flex flex-col gap-2"
                  >
                    <div className="flex justify-between items-center text-[10px] font-bold">
                      <span className="text-accent-cyan">@{match.chat_name}</span>
                      <span className="text-zinc-500 font-mono">{match.month}</span>
                    </div>
                    <p className="text-[11px] text-zinc-300 leading-relaxed font-sans italic">
                      &quot;{match.document}&quot;
                    </p>
                  </div>
                ))}
              </div>
            ) : globalSearchQuery.trim() ? (
              <div className="text-xs text-zinc-600 italic mt-4">
                No matching semantic blocks found.
              </div>
            ) : null}
          </div>

        </div>
      ) : (
        
        /* ==================== STATE B: ACTIVE CONTACT LOADING ASSESSMENT ==================== */
        <div className="flex-1 flex flex-col overflow-hidden relative">
          
          {/* Back Navigation */}
          <div className="p-3 border-b border-zinc-600 bg-[#1F1F23] shrink-0 flex items-center">
            <button 
              onClick={() => setSelectedContact(null)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-primary/30 bg-primary/15 text-xs font-bold text-white hover:bg-primary/25 hover:border-primary/50 transition-all cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back
            </button>
          </div>
          
          {/* Top Panel: Psychological Assessment Report (65% Height) */}
          <div className="h-[65%] border-b border-[var(--border-glass)] flex flex-col overflow-hidden p-5 bg-[rgba(10,10,12,0.05)]">
            
            {/* Setup Controls (When no profile is generated or during custom ranges) */}
            {!savedProfile && !isGeneratingProfile && (
              <div className="flex-1 flex flex-col justify-center items-center max-w-md mx-auto text-center gap-4">
                <FileText className="w-9 h-9 text-primary opacity-85" />
                <h3 className="font-outfit font-bold text-sm text-white">Generate Personality Assessment</h3>
                <p className="text-[11px] text-zinc-500 leading-relaxed">
                  Run a full behavioral scan to generate a psychological assessment report, extracting linguistic patterns, emotional sentiment, and personality traits.
                </p>

                <form onSubmit={handleGenerateProfile} className="w-full flex flex-col gap-3 mt-2 text-left">
                  {/* Range Selectors */}
                  {availableMonths.length > 0 && (
                    <div className="grid grid-cols-2 gap-2">
                      <div className="flex flex-col gap-1">
                        <label htmlFor="start-month" className="text-[9px] uppercase text-zinc-500 font-bold">Start Month</label>
                        <select 
                          id="start-month"
                          value={startMonth}
                          onChange={(e) => setSelectedStartMonth(e.target.value)}
                          className="px-2 py-1.5 bg-zinc-950 border border-[var(--border-glass)] rounded-lg text-[10px] text-white cursor-pointer"
                        >
                          {availableMonths.map(m => <option key={m} value={m}>{m.replace('.md','')}</option>)}
                        </select>
                      </div>

                      <div className="flex flex-col gap-1">
                        <label htmlFor="end-month" className="text-[9px] uppercase text-zinc-500 font-bold">End Month</label>
                        <select 
                          id="end-month"
                          value={endMonth}
                          onChange={(e) => setSelectedEndMonth(e.target.value)}
                          className="px-2 py-1.5 bg-zinc-950 border border-[var(--border-glass)] rounded-lg text-[10px] text-white cursor-pointer"
                        >
                          {availableMonths.map(m => <option key={m} value={m}>{m.replace('.md','')}</option>)}
                        </select>
                      </div>
                    </div>
                  )}

                  {/* AI engine config overrides */}
                  <div className="flex flex-col gap-2 p-3 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg mt-1">
                    <label className="text-[9px] uppercase text-zinc-500 font-bold flex items-center gap-1">
                      <Cpu className="w-3.5 h-3.5" /> AI Engine Router
                    </label>
                    
                    <div className="flex items-center justify-between text-[10px] mt-1">
                      <span className="text-zinc-400">Force Cloud (Gemini)</span>
                      <input 
                        type="checkbox" 
                        checked={forceCloud}
                        onChange={(e) => setForceCloud(e.target.checked)}
                        className="accent-primary"
                        aria-label="Force Cloud (Gemini)"
                      />
                    </div>

                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-zinc-400">Thorough Deep Scan</span>
                      <input 
                        type="checkbox" 
                        checked={deepScan}
                        onChange={(e) => setDeepScan(e.target.checked)}
                        className="accent-primary"
                        aria-label="Thorough Deep Scan"
                      />
                    </div>

                    <div className="flex items-center justify-between text-[10px] pt-1.5 border-t border-zinc-900 mt-1">
                      <span className="text-[#FF9500] font-bold">Cloud processing consent</span>
                      <input 
                        type="checkbox" 
                        checked={userConsent}
                        onChange={(e) => setUserConsent(e.target.checked)}
                        className="accent-[#FF9500]"
                        aria-label="Cloud processing consent"
                      />
                    </div>
                  </div>

                  <button 
                    type="submit"
                    className="w-full py-2 bg-primary hover:bg-primary/90 text-white text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-2 mt-2 cursor-pointer"
                  >
                    <Sparkles className="w-3.5 h-3.5" /> Generate Psychological Profile
                  </button>
                </form>
              </div>
            )}

            {/* Spinner when generating profile */}
            {isGeneratingProfile && (
              <div className="flex-1 flex flex-col justify-center items-center gap-3.5">
                <RefreshCw className="w-8 h-8 text-primary animate-spin glow-primary" />
                <p className="text-xs font-bold text-white">Analyzing conversation logs for {selectedContact}...</p>
                <p className="text-[10px] text-zinc-500">Retrieving vectors, indexing patterns, and dispatching to LLM.</p>
              </div>
            )}

            {/* Render assessment results */}
            {savedProfile && !isGeneratingProfile && (
              <div className="flex-1 flex flex-col overflow-hidden">
                
                {/* Header metadata */}
                <div className="flex items-center justify-between border-b border-[var(--border-glass)] pb-2 mb-3 shrink-0">
                  <div className="flex flex-col">
                    <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                      <Bot className="w-4 h-4 text-primary" /> Personality Profile Assessment
                    </h3>
                    <span className="text-[10px] text-zinc-500 mt-0.5">
                      Range: {profileMeta?.start_month?.replace('.md','')} to {profileMeta?.end_month?.replace('.md','')} | Engine: {profileMeta?.model}
                    </span>
                  </div>

                  {/* Actions: Compile PDF */}
                  <div className="flex gap-2">
                    {isPDFCompiled ? (
                  <button
                    onClick={handleDownloadPDF}
                    className="px-3 py-1 bg-success hover:bg-success/90 text-black font-bold text-[10px] rounded-md flex items-center gap-1 transition-all cursor-pointer"
                    aria-label="Download PDF report"
                  >
                        <Download className="w-3.5 h-3.5" /> Download PDF
                      </button>
                    ) : (
                    <button
                      onClick={handleCompilePDF}
                      disabled={isCompilingPDF}
                      className="px-3 py-1 bg-primary hover:bg-primary/90 disabled:bg-zinc-850 text-white font-bold text-[10px] rounded-md flex items-center gap-1 transition-all cursor-pointer"
                      aria-label="Compile PDF report"
                    >
                        {isCompilingPDF ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <FileText className="w-3.5 h-3.5" />
                        )}
                        Compile Report PDF
                      </button>
                    )}
                    
                    {/* Regenerate Trigger */}
                    <button 
                      onClick={() => clearProfile()}
                      className="px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-700 text-zinc-400 hover:text-white hover:bg-zinc-800 font-bold text-[10px] transition-all cursor-pointer"
                      aria-label="Regenerate profile"
                    >
                      Regenerate
                    </button>
                  </div>
                </div>

                {/* Profile text content scroll area */}
                <div className="flex-1 overflow-y-auto pr-1 space-y-3 font-sans text-xs leading-relaxed text-zinc-200 scrollbar-thin scrollbar-thumb-zinc-800 select-text">
                  <div className="prose prose-invert max-w-none prose-xs">
                    {/* Render raw markdown as styling (clean pre-wrap rendering) */}
                    <div className="whitespace-pre-wrap font-sans">{savedProfile}</div>
                  </div>
                  
                  {/* Disclaimer */}
                  <div className="p-3.5 mt-5 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg text-[10px] text-zinc-500 italic text-center leading-normal">
                    ⚠️ <b>Disclaimer:</b> The &quot;psychological profile&quot; is AI-generated analysis, not clinical psychology. This protects against liability.
                  </div>
                </div>

              </div>
            )}
            
          </div>

          {/* Bottom Panel: Interactive RAG Chat Box (35% Height) */}
          <div className="h-[35%] flex flex-col overflow-hidden bg-[rgba(10,10,12,0.15)] relative">
            
            {/* Conversation list */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-zinc-800">
              {ragChatHistory.length > 0 ? (
                ragChatHistory.map((msg, idx) => {
                  return (
                    <div 
                      key={msg.time + msg.sender + idx}
                      className={`flex flex-col max-w-[85%] ${msg.sender === 'user' ? 'ml-auto items-end' : 'mr-auto items-start'}`}
                    >
                      <div 
                        className={`p-2.5 rounded-lg border flex flex-col text-xs leading-normal font-sans shadow-md ${
                          msg.sender === 'user'
                            ? 'bg-[rgba(121,99,255,0.06)] border-[rgba(121,99,255,0.2)] rounded-tr-sm'
                            : 'bg-[rgba(255,255,255,0.02)] border-[var(--border-glass)] rounded-tl-sm'
                        }`}
                      >
                        <div className="flex items-center gap-4 justify-between mb-1">
                          <strong className="text-[9px] font-bold uppercase text-primary flex items-center gap-1">
                            {msg.sender === 'user' ? <User className="w-3 h-3" /> : <Bot className="w-3 h-3" />}
                            {msg.sender === 'user' ? 'Me (User)' : 'Intelligence RAG'}
                          </strong>
                          <span className="text-[8px] text-zinc-500 font-mono">{msg.time}</span>
                        </div>
                        {(() => {
                          const err = msg.error;
                          if (err) {
                            return (
                              <div className="flex flex-col gap-2 mt-1 p-2.5 bg-[rgba(255,69,58,0.05)] border border-[rgba(255,69,58,0.15)] rounded-lg text-[11px] text-zinc-300">
                                <span className="text-error font-bold">Query Failed</span>
                                <p className="text-zinc-400 text-[10px] leading-relaxed">{err.message}</p>
                                {err.can_retry && (
                                  <button 
                                    onClick={() => {
                                      if (selectedContact) {
                                        queryRAG(
                                          selectedContact, 
                                          err.query, 
                                          err.start_month, 
                                          err.end_month, 
                                          err.deep_scan, 
                                          err.user_consent
                                        );
                                      }
                                    }}
                                    className="mt-1.5 px-2.5 py-1 bg-error hover:bg-error/90 text-white text-[9px] font-bold rounded flex items-center gap-1 cursor-pointer self-start shadow-sm"
                                  >
                                    <RefreshCw className="w-2.5 h-2.5" />
                                    Retry Query
                                  </button>
                                )}
                              </div>
                            );
                          }
                          return <div className="text-zinc-200 whitespace-pre-wrap">{msg.text}</div>;
                        })()}
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="h-full flex items-center justify-center text-[11px] text-zinc-500 italic text-center gap-1.5 select-none">
                  <MessageSquare className="w-4 h-4 text-zinc-600" />
                  Ask AI anything about DMs history. Response history shows here.
                </div>
              )}
              {isQueryingRAG && (
                <div className="mr-auto flex items-center gap-2 p-2 bg-[rgba(255,255,255,0.01)] border border-[var(--border-glass)] rounded-lg text-xs text-zinc-400">
                  <RefreshCw className="w-3 h-3 animate-spin text-primary" />
                  <span>Searching vector index...</span>
                </div>
              )}
              <div ref={threadEndRef} />
            </div>

            {/* Input field */}
            <form 
              onSubmit={handleRAGQuerySubmit}
              className="p-3 border-t border-[var(--border-glass)] bg-[rgba(10,10,12,0.35)] shrink-0 flex gap-2"
            >
              <input 
                type="text"
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                disabled={isQueryingRAG}
                placeholder={`Ask AI anything about @${selectedContact}'s DMs logs...`}
                className="flex-1 px-4 py-2 bg-[rgba(255,255,255,0.015)] border border-[var(--border-glass)] rounded-lg text-xs text-white outline-none focus:border-primary transition-colors disabled:opacity-50"
              />
              <button 
                type="submit"
                disabled={isQueryingRAG || !ragQuery.trim()}
                className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-30 text-white font-bold text-xs rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" /> Send
              </button>
            </form>

          </div>

        </div>
      )}

    </div>
  );
}
