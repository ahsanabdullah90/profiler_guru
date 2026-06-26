'use client';

import React, { useEffect, useRef } from 'react';
import { useSyncStore, getWsUrl, getApiBase } from '../store/useSyncStore';
import { Cpu, RefreshCw, Layers, Globe, Server, AlertCircle } from 'lucide-react';

export default function StatusBar() {
  const { status, setStatus } = useSyncStore();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // WebSocket Connection Lifecycle & HTTP Polling Fallback management
  useEffect(() => {
    let reconnectDelay = 1000;
    let isWsOnline = false;

    // HTTP Polling Fallback: queries GET /api/status every 3 seconds
    const startHttpPolling = () => {
      if (pollingIntervalRef.current) return;
      
      logger_debug('Starting HTTP status polling fallback...');
      
      const pollStatus = async () => {
        if (isWsOnline) return; // Skip if WebSocket came online
        try {
          const res = await fetch(`${getApiBase()}/api/status`);
          if (res.ok) {
            const data = await res.json();
            setStatus({
              app_online: true,
              instagram_sync: data.instagram_sync,
              transcription: data.transcription,
              rag: data.rag,
              online_llm: data.online_llm,
              ollama: data.ollama
            });
          } else {
            setStatus({ app_online: false });
          }
        } catch (e) {
          setStatus({ app_online: false });
          console.warn('HTTP status polling fallback failed to connect to backend.');
        }
      };

      // Poll immediately and then every 3 seconds
      pollStatus();
      pollingIntervalRef.current = setInterval(pollStatus, 3000);
    };

    const stopHttpPolling = () => {
      if (pollingIntervalRef.current) {
        logger_debug('Stopping HTTP status polling fallback.');
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };

    const connectWS = () => {
      if (wsRef.current) return;

      try {
        const ws = new WebSocket(getWsUrl());
        wsRef.current = ws;

        ws.onopen = () => {
          logger_debug('WebSocket status connection established.');
          isWsOnline = true;
          setStatus({ app_online: true });
          reconnectDelay = 1000; // Reset delay
          stopHttpPolling(); // Stop HTTP polling since WebSocket is online
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'status_update') {
              setStatus({
                app_online: data.app_online,
                instagram_sync: data.instagram_sync,
                transcription: data.transcription,
                rag: data.rag,
                online_llm: data.online_llm,
                ollama: data.ollama
              });
            }
          } catch (err) {
            console.error('Error parsing status WS message:', err);
          }
        };

        ws.onclose = () => {
          wsRef.current = null;
          isWsOnline = false;
          setStatus({ app_online: false });
          logger_debug('WebSocket status connection closed. Attempting reconnect...');
          
          // Start HTTP polling fallback as soon as the WebSocket goes offline
          startHttpPolling();
          
          // Exponential backoff reconnect
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
            connectWS();
          }, reconnectDelay);
        };

        ws.onerror = (err) => {
          console.error('WebSocket status connection error (PNA/adblocker restriction likely):', err);
          ws.close();
        };
      } catch (e) {
        console.error('Failed to create WebSocket:', e);
        startHttpPolling();
      }
    };

    // Attempt WebSocket connection, and start HTTP polling as a parallel fallback
    connectWS();
    startHttpPolling();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent trigger on cleanup
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [setStatus]);


  function logger_debug(msg: string) {
    console.log(`[StatusMonitor] ${msg}`);
  }

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
