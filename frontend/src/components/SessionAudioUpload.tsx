'use client';

import React, { useRef, useState } from 'react';
import { apiFetch, getApiBase } from '../store/api';
import { Loader2, Upload, CheckCircle, XCircle, Mic, FileAudio } from 'lucide-react';

interface Props {
  contactName: string;
}

export default function SessionAudioUpload({ contactName }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ session_id: string; status: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const authToken = localStorage.getItem('auth_token');
      const apiBase = getApiBase();
      const res = await fetch(`${apiBase}/clinical/${encodeURIComponent(contactName)}/audio/upload`, {
        method: 'POST',
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(typeof err.detail === 'object' ? err.detail.message || 'Upload failed' : err.detail || 'Upload failed');
      }

      const data = await res.json();
      setResult({ session_id: data.session_id, status: data.status });
    } catch (err) {
      const e = err as Error;
      setError(e.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <p className="text-[9px] text-[var(--text-muted)] italic leading-relaxed">
        Upload a session recording (MP3, M4A, WAV, OGG). Transcription will be processed in the background.
      </p>

      <input
        ref={fileInputRef}
        type="file"
        accept=".mp3,.m4a,.wav,.ogg,.webm"
        className="hidden"
        onChange={handleFileChange}
      />

      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        className="w-full py-2 rounded-lg text-[10px] font-bold flex items-center justify-center gap-2 cursor-pointer disabled:opacity-40 transition-all"
        style={{ background: 'var(--bg-surface)', border: '1px dashed var(--border-subtle)', color: 'var(--text-secondary)' }}
      >
        {uploading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Mic className="w-3.5 h-3.5" />
        )}
        {uploading ? 'Uploading & processing...' : 'Upload Session Audio'}
      </button>

      {result ? (
        <div className="flex items-center gap-2 p-2 rounded-lg text-[10px]" style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)', color: '#10B981' }}>
          <CheckCircle className="w-3 h-3 shrink-0" />
          Audio uploaded. Transcription in progress.
        </div>
      ) : null}

      {error ? (
        <div className="flex items-center gap-2 p-2 rounded-lg text-[10px]" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#EF4444' }}>
          <XCircle className="w-3 h-3 shrink-0" />
          {error}
        </div>
      ) : null}
    </div>
  );
}
