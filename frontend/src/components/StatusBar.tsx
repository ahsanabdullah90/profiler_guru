'use client';

import React, { useEffect, useRef } from 'react';
import { useSyncStore } from '../store/useSyncStore';
import { StatusService } from '../services/StatusService';
import { Cpu, RefreshCw, Layers, Globe, Server } from 'lucide-react';

export default function StatusBar() {
  const { status, setStatus } = useSyncStore();
  const serviceRef = useRef<StatusService | null>(null);

  useEffect(() => {
    const service = new StatusService(
      (update) => setStatus(update),
    );
    serviceRef.current = service;
    service.start();

    return () => {
      service.stop();
      serviceRef.current = null;
    };
  }, [setStatus]);

  return (
    <footer className="h-[40px] w-full px-6 flex items-center justify-between border-t border-[var(--border-glass)] bg-[rgba(10,10,12,0.6)] backdrop-blur-md relative z-30 text-[11px] font-medium text-zinc-400 select-none font-sans">
      {/* Left Area: Connection & Background Sync Monitor */}
      <div className="flex items-center gap-5">
        {/* App Server Connection Dot */}
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${status.app_online ? 'bg-[#32D74B] animate-led-pulse' : 'bg-[#FF375F]'}`} />
          <span className="font-bold text-zinc-300">
            App: {status.app_online ? 'Online' : 'Offline'}
          </span>
        </div>

        {/* Live Instagram Sync */}
        <div className="flex items-center gap-2 border-l border-zinc-800 pl-5">
          <RefreshCw className={`w-3.5 h-3.5 ${status.instagram_sync.status === 'syncing' ? 'animate-spin text-[#007AFF]' : 'text-zinc-500'}`} />
          {status.instagram_sync.status === 'syncing' ? (
            <span>
              Sync: <strong className="text-[#007AFF]">@{status.instagram_sync.contact}</strong>
              {status.instagram_sync.total > 0 && (
                <span className="text-zinc-500 ml-1">
                  ({status.instagram_sync.current}/{status.instagram_sync.total} DMs)
                </span>
              )}
            </span>
          ) : (
            <span>Sync: <strong className="text-zinc-500">Idle</strong></span>
          )}
        </div>
      </div>

      {/* Middle Area: Heavy Task Queues (STT & RAG Indexing) */}
      <div className="flex items-center gap-5">
        {/* Whisper Audio Transcription Queue */}
        <div className="flex items-center gap-2">
          <Cpu className={`w-3.5 h-3.5 ${status.transcription.status === 'transcribing' ? 'text-[#FF9500] animate-pulse' : 'text-zinc-500'}`} />
          {status.transcription.status === 'transcribing' ? (
            <span>
              Transcribing: <strong className="text-[#FF9500]">{status.transcription.contact}</strong>
              {status.transcription.total > 0 && (
                <span className="text-zinc-500 ml-1">
                  ({status.transcription.current}/{status.transcription.total} clips)
                </span>
              )}
            </span>
          ) : (
            <span>Transcribing: <strong className="text-zinc-500">Idle</strong></span>
          )}
        </div>

        {/* ChromaDB RAG Vector Indexer Status */}
        <div className="flex items-center gap-2 border-l border-zinc-800 pl-5">
          <Layers className={`w-3.5 h-3.5 ${status.rag.status === 'indexing' ? 'text-[#007AFF] animate-bounce' : 'text-zinc-500'}`} />
          {status.rag.status === 'indexing' ? (
            <span>
              RAG: <strong className="text-[#007AFF]">Indexing {status.rag.contact}</strong>
              <span className="text-zinc-500 ml-1">({status.rag.progress}%)</span>
            </span>
          ) : (
            <span>RAG: <strong className="text-zinc-500">Upto Date</strong></span>
          )}
        </div>
      </div>

      {/* Right Area: LLM Engine Provider Handshakes */}
      <div className="flex items-center gap-5 border-l border-zinc-800 pl-5">
        {/* Cloud LLM Google Gemini Status */}
        <div className="flex items-center gap-1.5">
          <Globe className="w-3.5 h-3.5 text-zinc-500" />
          <span>Cloud ({status.online_llm.model}):</span>
          <span className={`font-bold ${status.online_llm.online ? 'text-[#32D74B]' : 'text-[#FF375F]'}`}>
            {status.online_llm.online ? 'Online' : 'Offline'}
          </span>
        </div>

        {/* Local LLM Ollama Status */}
        <div className="flex items-center gap-1.5 border-l border-zinc-800 pl-5">
          <Server className="w-3.5 h-3.5 text-zinc-500" />
          <span>Ollama ({status.ollama.model}):</span>
          <span className={`font-bold ${status.ollama.online ? 'text-[#32D74B]' : 'text-[#FF375F]'}`}>
            {status.ollama.online ? 'Online' : 'Offline'}
          </span>
        </div>
      </div>
    </footer>
  );
}
