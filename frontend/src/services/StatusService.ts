import type { SystemStatus } from '../store/useSyncStore';
import { fetchWithTimeout } from '../store/useSyncStore';
import { WsProtocolClient, type StatusUpdatePayload } from '../lib/ws';

export type ConnectionState = 'connecting' | 'connected' | 'disconnected';

export type StatusUpdateCallback = (status: Partial<SystemStatus>) => void;
export type ConnectionCallback = (state: ConnectionState) => void;

type Transport = 'ws' | 'sse' | 'polling';

function sseUrl(): string {
  const host = typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1';
  return `http://${host}:8000/api/events`;
}

function pollingUrl(): string {
  const host = typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1';
  return `http://${host}:8000/api/v1/status`;
}

function wsUrl(): string {
  const host = typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1';
  return `ws://${host}:8000/ws/status`;
}

/**
 * Negotiates transports: WebSocket → SSE → HTTP polling.
 * All transports feed the same onStatusUpdate callback.
 */
export class StatusService {
  private wsClient: WsProtocolClient | null = null;
  private sseSource: EventSource | null = null;
  private pollingInterval: ReturnType<typeof setInterval> | null = null;
  private destroyed = false;
  private currentTransport: Transport | null = null;
  private onStatusUpdate: StatusUpdateCallback;
  private onConnectionChange: ConnectionCallback;

  constructor(
    onStatusUpdate: StatusUpdateCallback,
    onConnectionChange?: ConnectionCallback
  ) {
    this.onStatusUpdate = onStatusUpdate;
    this.onConnectionChange = onConnectionChange || (() => {});
  }

  start(): void {
    if (this.destroyed) return;
    this.tryWebSocket();
  }

  stop(): void {
    this.destroyed = true;
    this.teardownCurrent();
  }

  private teardownCurrent(): void {
    if (this.wsClient) {
      this.wsClient.close();
      this.wsClient = null;
    }
    this.closeSSE();
    this.stopPolling();
    this.currentTransport = null;
  }

  private tryWebSocket(): void {
    if (this.destroyed) return;
    this.teardownCurrent();
    this.currentTransport = 'ws';

    this.wsClient = new WsProtocolClient({
      onStatusUpdate: (payload: StatusUpdatePayload) => {
        this.onStatusUpdate(payload);
      },
      onConnectionChange: (state) => {
        if (state === 'connected') {
          this.currentTransport = 'ws';
          this.closeSSE();
          this.stopPolling();
          this.onConnectionChange('connected');
        } else if (state === 'disconnected') {
          this.onConnectionChange('disconnected');
          // WS failed — try SSE
          if (this.currentTransport === 'ws') {
            this.trySSE();
          }
        } else {
          this.onConnectionChange('connecting');
        }
      },
    });

    this.wsClient.connect(wsUrl());
  }

  private trySSE(): void {
    if (this.destroyed || this.currentTransport !== 'ws') return;
    this.currentTransport = 'sse';

    try {
      const source = new EventSource(sseUrl());
      this.sseSource = source;
      this.onConnectionChange('connecting');

      source.onopen = () => {
        if (this.destroyed) { source.close(); return; }
        this.stopPolling();
        this.onConnectionChange('connected');
      };

      source.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'status_update' && data.payload) {
            this.onStatusUpdate(data.payload);
          }
        } catch (err) {
          console.error('[StatusService] SSE parse error:', err);
        }
      };

      source.onerror = () => {
        this.sseSource = null;
        this.onConnectionChange('disconnected');
        // SSE failed — fall back to HTTP polling
        if (this.currentTransport === 'sse') {
          this.startPolling();
        }
      };
    } catch (e) {
      console.error('[StatusService] SSE connection failed:', e);
      this.sseSource = null;
      this.startPolling();
    }
  }

  private closeSSE(): void {
    if (this.sseSource) {
      this.sseSource.close();
      this.sseSource = null;
    }
  }

  private startPolling(): void {
    if (this.pollingInterval || this.destroyed) return;
    this.currentTransport = 'polling';
    this.onConnectionChange('connecting');

    const poll = async () => {
      if (this.destroyed) return;
      try {
        const res = await fetchWithTimeout(pollingUrl(), {}, 3000);
        if (res.ok) {
          const data = await res.json();
          this.onStatusUpdate({
            app_online: data.app_online ?? false,
            instagram_sync: data.instagram_sync,
            transcription: data.transcription,
            rag: data.rag,
            online_llm: data.online_llm,
            ollama: data.ollama,
          });
          this.onConnectionChange('connected');
        } else {
          this.onStatusUpdate({ app_online: false });
          this.onConnectionChange('disconnected');
        }
      } catch {
        this.onStatusUpdate({ app_online: false });
        this.onConnectionChange('disconnected');
      }
    };

    poll();
    this.pollingInterval = setInterval(poll, 3000);
  }

  private stopPolling(): void {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }
}
