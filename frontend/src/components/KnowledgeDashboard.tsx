'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import { useStatusStore } from '../store/statusStore';
import { getApiBase, apiFetch, ApiError } from '../store/api';
import {
  BookOpen,
  Upload,
  Trash2,
  Send,
  Loader2,
  FileText,
  User,
  Calendar,
  AlertCircle,
  HelpCircle,
  CheckCircle,
  RefreshCw,
  X,
  FileUp,
} from 'lucide-react';

interface KnowledgeDocument {
  document_id: string;
  filename: string;
  filepath: string;
  title: string;
  author: string | null;
  year: number | null;
  embedding_status: 'indexing' | 'completed' | 'failed';
  uploaded_at: string;
}

interface CitationInfo {
  source_id: number;
  title: string;
  author: string;
  year: number;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  citations: CitationInfo[];
}

export default function KnowledgeDashboard() {
  const token = useAuthStore((s) => s.token);
  const pushError = useStatusStore((s) => s.pushError);

  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Upload Form State
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [year, setYear] = useState('');

  // Delete Double Confirmation Modal
  const [docToDelete, setDocToDelete] = useState<KnowledgeDocument | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');

  // Chat Window State
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Welcome to the Psychology Knowledge Base Chat. Ask me questions, and I will answer strictly based on the uploaded books and reference literature.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      citations: [],
    },
  ]);
  const [chatInput, setChatInput] = useState('');
  const [sendingQuery, setSendingQuery] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // 1. Fetch Ingested Documents
  const fetchDocuments = useCallback(async () => {
    setLoadingDocs(true);
    try {
      const data = await apiFetch<{ documents: KnowledgeDocument[] }>('/knowledge');
      setDocuments(data.documents);
    } catch (err) {
      const e = err as Error;
      pushError(`Failed to load knowledge base: ${e.message}`, 'error');
    } finally {
      setLoadingDocs(false);
    }
  }, [pushError]);

  useEffect(() => {
    const initialTimeout = setTimeout(() => {
      fetchDocuments();
    }, 0);
    // Poll document statuses every 5 seconds to track background indexing progress
    const interval = setInterval(fetchDocuments, 5000);
    return () => {
      clearTimeout(initialTimeout);
      clearInterval(interval);
    };
  }, [fetchDocuments]);

  // Scroll chat window to bottom
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // 2. Handle File Ingestion
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title.trim()) return;
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title.trim());
      if (author.trim()) formData.append('author', author.trim());
      if (year.trim()) formData.append('year', year.trim());

      const res = await fetch(`${getApiBase()}/knowledge`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      pushError(`Document "${title}" queued for indexing.`, 'info');
      // Reset Form
      setFile(null);
      setTitle('');
      setAuthor('');
      setYear('');
      fetchDocuments();
    } catch (err) {
      const e = err as Error;
      pushError(`Failed to upload document: ${e.message}`, 'error');
    } finally {
      setUploading(false);
    }
  };

  // 3. Handle Document Deletion
  const handleDelete = async () => {
    if (!docToDelete) return;
    setIsDeleting(true);
    try {
      await apiFetch(`/knowledge/${docToDelete.document_id}`, {
        method: 'DELETE',
      });
      pushError(`Document "${docToDelete.title}" removed.`, 'info');
      setDocToDelete(null);
      setDeleteConfirmText('');
      fetchDocuments();
    } catch (err) {
      const e = err as Error;
      pushError(`Deletion failed: ${e.message}`, 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  // 4. Handle Q&A Chat Query
  const handleSendQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = chatInput.trim();
    if (!query || sendingQuery) return;

    // Append user message
    const userMsgId = `${Date.now()}-user`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      citations: [],
    };
    setMessages((prev) => [...prev, userMsg]);
    setChatInput('');
    setSendingQuery(true);

    try {
      const res = await apiFetch<{ response: string; citations: CitationInfo[] }>('/knowledge/query', {
        method: 'POST',
        body: JSON.stringify({ query }),
      });

      const assistantMsg: ChatMessage = {
        id: `${Date.now()}-assistant`,
        sender: 'assistant',
        text: res.response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        citations: res.citations,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const e = err as Error;
      pushError(`Query failed: ${e.message}`, 'error');
      const errorMsg: ChatMessage = {
        id: `${Date.now()}-error`,
        sender: 'assistant',
        text: 'Sorry, I encountered an error while retrieving literature context.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        citations: [],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSendingQuery(false);
    }
  };

  // Drag and Drop Helpers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const dropped = e.dataTransfer.files[0];
      const suffix = dropped.name.slice(dropped.name.lastIndexOf('.')).toLowerCase();
      if (['.pdf', '.txt', '.md'].includes(suffix)) {
        setFile(dropped);
        setTitle(dropped.name.substring(0, dropped.name.lastIndexOf('.')));
      } else {
        pushError('Invalid file type. Only PDF, TXT, or MD are supported.', 'error');
      }
    }
  };

  // Strict local String extension safety polyfill
  const hasTitle = title && typeof title === 'string' && title.trim().length > 0;

  return (
    <div className="h-full flex flex-col overflow-hidden bg-[var(--bg-canvas)] relative font-sans text-white">
      {/* Dynamic Ambient Background Elements */}
      <div className="ambient-glow -top-30 -right-30" />
      
      {/* Header */}
      <header className="h-[56px] px-6 border-b border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] flex items-center justify-between shrink-0 z-10">
        <div className="flex items-center gap-2.5">
          <BookOpen className="w-4 h-4 text-[var(--brand-primary)]" />
          <h2 className="text-sm font-bold tracking-tight">Psychology Knowledge Base</h2>
        </div>
      </header>

      {/* Main panel layout */}
      <div className="flex-1 flex min-h-0 overflow-hidden relative z-10">
        
        {/* LEFT COLUMN: Document Manager */}
        <div className="w-[45%] border-r border-[var(--border-subtle)] bg-[var(--bg-surface)] flex flex-col min-h-0 overflow-hidden p-6 gap-6">
          
          {/* Section: Upload Document */}
          <div className="glass-panel p-5 border border-[var(--border-glass)] rounded-2xl flex flex-col gap-4 relative">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Upload Reference Document</h3>
            
            <form onSubmit={handleUpload} className="space-y-3.5">
              {/* Drag/Drop Box */}
              <div
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-4 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors ${
                  file ? 'border-[var(--brand-primary)] bg-[var(--brand-primary-soft)]/5' : 'border-[var(--border-subtle)] hover:border-zinc-500'
                }`}
                onClick={() => document.getElementById('file-upload-input')?.click()}
              >
                <input
                  id="file-upload-input"
                  type="file"
                  accept=".pdf,.txt,.md"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      const selected = e.target.files[0];
                      setFile(selected);
                      setTitle(selected.name.substring(0, selected.name.lastIndexOf('.')));
                    }
                  }}
                />
                {file ? (
                  <>
                    <CheckCircle className="w-6 h-6 text-emerald-400" />
                    <span className="text-[11px] text-zinc-300 font-mono text-center truncate max-w-xs">{file.name}</span>
                    <span className="text-[9px] text-zinc-500">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                  </>
                ) : (
                  <>
                    <FileUp className="w-6 h-6 text-zinc-400" />
                    <span className="text-[11px] text-zinc-300">Drag PDF/TXT file here or click to browse</span>
                    <span className="text-[9px] text-zinc-500">Supported types: PDF, TXT, MD</span>
                  </>
                )}
              </div>

              {/* Text Fields */}
              <div className="grid grid-cols-2 gap-3.5">
                <div className="col-span-2">
                  <label htmlFor="doc-title" className="text-[10px] text-zinc-400 block mb-1 font-semibold">Document Title *</label>
                  <input
                    id="doc-title"
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Attachment Theory Basics"
                    className="w-full h-8 px-2.5 bg-[var(--bg-surface-inset)] border border-[var(--border-subtle)] rounded-lg text-xs outline-none focus:border-[var(--brand-primary)] text-white"
                  />
                </div>
                <div>
                  <label htmlFor="doc-author" className="text-[10px] text-zinc-400 block mb-1 font-semibold">Author / Publisher</label>
                  <input
                    id="doc-author"
                    type="text"
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                    placeholder="e.g. John Bowlby"
                    className="w-full h-8 px-2.5 bg-[var(--bg-surface-inset)] border border-[var(--border-subtle)] rounded-lg text-xs outline-none focus:border-[var(--brand-primary)] text-white"
                  />
                </div>
                <div>
                  <label htmlFor="doc-year" className="text-[10px] text-zinc-400 block mb-1 font-semibold">Publication Year</label>
                  <input
                    id="doc-year"
                    type="number"
                    value={year}
                    onChange={(e) => setYear(e.target.value)}
                    placeholder="e.g. 1969"
                    className="w-full h-8 px-2.5 bg-[var(--bg-surface-inset)] border border-[var(--border-subtle)] rounded-lg text-xs outline-none focus:border-[var(--brand-primary)] font-mono text-white"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={uploading || !file || !hasTitle}
                className="w-full h-9 bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-strong)] disabled:opacity-40 disabled:hover:bg-[var(--brand-primary)] text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 shadow-md shadow-purple-500/10 cursor-pointer"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Processing & Indexing…</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload & Vectorize</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Section: Document Library */}
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="flex items-center justify-between mb-3 shrink-0">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">Document Library</h3>
              {loadingDocs && <RefreshCw className="w-3 h-3 text-[var(--text-muted)] animate-spin" />}
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-3.5 min-h-0 pr-1">
              {documents.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-8 text-center text-[var(--text-muted)] gap-2 h-full">
                  <FileText className="w-8 h-8 opacity-30" />
                  <span className="text-xs">No reference literature ingested yet.</span>
                </div>
              ) : (
                documents.map((doc) => (
                  <div key={doc.document_id} className="p-4 rounded-xl border border-[var(--border-glass)] bg-[var(--bg-surface-raised)] flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="p-2 rounded-lg bg-[rgba(255,255,255,0.03)] border border-zinc-800 shrink-0">
                        <FileText className="w-4 h-4 text-purple-400" />
                      </div>
                      <div className="min-w-0 space-y-1">
                        <h4 className="text-xs font-bold text-white leading-tight truncate" title={doc.title}>{doc.title}</h4>
                        <p className="text-[10px] text-zinc-400 flex items-center gap-1.5">
                          {doc.author && <span className="flex items-center gap-1"><User className="w-2.5 h-2.5" />{doc.author}</span>}
                          {doc.year && <span className="flex items-center gap-1"><Calendar className="w-2.5 h-2.5" />{doc.year}</span>}
                        </p>
                        <p className="text-[9px] text-zinc-500 truncate font-mono">{doc.filename}</p>
                      </div>
                    </div>
                    
                    {/* Status & Delete */}
                    <div className="flex flex-col items-end gap-2 shrink-0">
                      {doc.embedding_status === 'indexing' && (
                        <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/25 flex items-center gap-1">
                          <Loader2 className="w-2.5 h-2.5 animate-spin" /> Indexing
                        </span>
                      )}
                      {doc.embedding_status === 'completed' && (
                        <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
                          Completed
                        </span>
                      )}
                      {doc.embedding_status === 'failed' && (
                        <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/25">
                          Failed
                        </span>
                      )}
                      
                      <button
                        onClick={() => setDocToDelete(doc)}
                        className="p-1.5 rounded-lg border border-[var(--border-glass)] hover:bg-rose-500/10 hover:border-rose-500/30 text-zinc-500 hover:text-rose-400 transition-colors cursor-pointer"
                        title="Delete Document"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Knowledge Chat Window */}
        <div className="w-[55%] flex flex-col min-h-0 overflow-hidden bg-[var(--bg-surface-inset)]">
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-0">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} mb-1`}>
                <div className={`max-w-[85%] p-4 rounded-2xl ${
                  msg.sender === 'user'
                    ? 'bg-[var(--brand-primary-soft)] border border-[var(--brand-primary)] rounded-br-sm'
                    : 'bg-[var(--bg-surface)] border border-[var(--border-glass)] rounded-bl-sm'
                }`}>
                  {/* Message body text */}
                  <p className="text-[11.5px] text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                  
                  {/* Citations bibliography list */}
                  {msg.citations.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-zinc-800 space-y-1.5">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-purple-400 block mb-1">References Match:</span>
                      {msg.citations.map((c) => (
                        <div key={c.source_id} className="text-[10px] text-zinc-400 font-serif leading-tight">
                          <span className="font-mono text-purple-300 font-bold mr-1.5">[{c.source_id}]</span>
                          {c.author} ({c.year}). <i>{c.title}</i>.
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <p className="text-[8px] text-[var(--text-muted)] mt-1.5 text-right font-mono">{msg.timestamp}</p>
                </div>
              </div>
            ))}
            {sendingQuery && (
              <div className="flex justify-start">
                <div className="bg-[var(--bg-surface)] border border-[var(--border-glass)] p-3 rounded-2xl rounded-bl-sm flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 text-[var(--brand-primary)] animate-spin" />
                  <span className="text-[10px] text-zinc-400">Searching literature database…</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Inputs */}
          <div className="p-4 border-t border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] shrink-0">
            <form onSubmit={handleSendQuery} className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask the psychology knowledge base..."
                className="flex-1 h-9 px-3 bg-[var(--bg-surface-inset)] border border-[var(--border-subtle)] rounded-xl text-xs outline-none focus:border-[var(--brand-primary)] text-white"
              />
              <button
                type="submit"
                disabled={sendingQuery || !chatInput.trim()}
                className="h-9 px-4 bg-[var(--brand-primary)] hover:bg-[var(--brand-primary-strong)] disabled:opacity-40 disabled:hover:bg-[var(--brand-primary)] text-white rounded-xl flex items-center justify-center cursor-pointer shadow-md shadow-purple-500/10"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </div>

      </div>

      {/* DOUBLE CONFIRMATION DELETION MODAL */}
      {docToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="w-full max-w-sm bg-[var(--bg-surface-raised)] border border-rose-500/35 rounded-2xl p-6 shadow-2xl space-y-4">
            
            {/* Warning Header */}
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 shrink-0">
                <AlertCircle className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-bold text-white">Wipe Knowledge Source</h3>
                <p className="text-[10px] text-zinc-400 mt-1 leading-relaxed">
                  Deleting this document is a permanent operation. All embedded vector index chunks will be wiped.
                </p>
              </div>
            </div>

            {/* Target details */}
            <div className="p-3 rounded-lg bg-black/25 border border-zinc-800 text-[10px]">
              <div className="text-zinc-400 uppercase tracking-wider text-[8px] mb-1 font-mono">Literature Target:</div>
              <div className="font-bold text-white leading-snug">{docToDelete.title}</div>
              <div className="text-zinc-500 font-mono text-[9px] mt-0.5 truncate">{docToDelete.filename}</div>
            </div>

            {/* Input field validation */}
            <div className="space-y-1">
              <label htmlFor="wipe-confirm" className="text-[9px] text-zinc-400 block font-mono">
                Type the word <span className="text-rose-400 font-bold font-mono">WIPE</span> below to confirm:
              </label>
              <input
                id="wipe-confirm"
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="WIPE"
                className="w-full h-8 px-2.5 bg-[var(--bg-surface-inset)] border border-zinc-800 focus:border-rose-500 rounded-lg text-xs outline-none font-mono tracking-widest text-center text-white"
              />
            </div>

            {/* Buttons */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setDocToDelete(null);
                  setDeleteConfirmText('');
                }}
                className="flex-1 h-8 border border-[var(--border-glass)] hover:bg-zinc-800 text-[10px] font-bold rounded-xl cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleteConfirmText !== 'WIPE' || isDeleting}
                onClick={handleDelete}
                className="flex-1 h-8 bg-rose-500 hover:bg-rose-600 disabled:opacity-40 disabled:hover:bg-rose-500 text-white text-[10px] font-bold rounded-xl flex items-center justify-center gap-1.5 shadow-md shadow-rose-500/10 cursor-pointer"
              >
                {isDeleting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
                <span>Confirm Deletion</span>
              </button>
            </div>
            
          </div>
        </div>
      )}
    </div>
  );
}
