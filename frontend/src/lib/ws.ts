// WebSocket Protocol v1 — typed client for status/task streaming

// ── Message Types ──────────────────────────────────────────────────────────────

export interface PingMessage { type: 'ping'; seq: number }
export interface PongMessage { type: 'pong'; seq: number }
export interface SubscribeMessage {
  type: 'subscribe';
  channels: Array<'status' | 'tasks'>;
  seq: number;
}

export interface StatusUpdatePayload {
  app_online: boolean;
  instagram_sync: { status: 'idle' | 'syncing'; contact: string; current: number; total: number };
  transcription: { status: 'idle' | 'transcribing'; contact: string; current: number; total: number };
  rag: { status: 'idle' | 'indexing'; contact: string; progress: number };
  online_llm: { model: string; online: boolean };
  ollama: { model: string; online: boolean };
}

export interface TaskEventPayload {
  task_id: string;
  event: 'started' | 'progress' | 'completed' | 'failed';
  progress?: number;
  message?: string;
}

export interface StatusUpdateMessage {
  type: 'status_update';
  seq: number;
  payload: StatusUpdatePayload;
  ts: number;
}

export interface TaskEventMessage {
  type: 'task_event';
  seq: number;
  payload: TaskEventPayload;
  ts: number;
}

export interface ErrorMessage {
  type: 'error';
  seq: number;
  code: string;
  message: string;
}

export interface HeartbeatMessage {
  type: 'heartbeat';
  ts: number;
}

export type ServerMessage =
  | StatusUpdateMessage
  | TaskEventMessage
  | ErrorMessage
  | HeartbeatMessage
  | PongMessage;

export type ClientMessage =
  | PingMessage
  | SubscribeMessage
  | PongMessage;

// ── Callbacks ──────────────────────────────────────────────────────────────────

export interface WsCallbacks {
  onStatusUpdate?: (payload: StatusUpdatePayload) => void;
  onTaskEvent?: (payload: TaskEventPayload) => void;
  onError?: (code: string, message: string) => void;
  onConnectionChange?: (state: 'connecting' | 'connected' | 'disconnected') => void;
}

// ── Client ─────────────────────────────────────────────────────────────────────

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 30000];
const JITTER_RANGE = 250;
const PING_INTERVAL_MS = 10000;
const HEARTBEAT_TIMEOUT_MS = 45000;

export class WsProtocolClient {
  private ws: WebSocket | null = null;
  private destroyed = false;
  private seq = 0;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null;
  private lastHeartbeat = 0;
  private callbacks: WsCallbacks;
  private subscribedChannels: Array<'status' | 'tasks'> = ['status'];

  constructor(callbacks: WsCallbacks) {
    this.callbacks = callbacks;
  }

  private nextSeq(): number {
    return ++this.seq;
  }

  connect(url: string): void {
    if (this.destroyed || this.ws) return;
    this.callbacks.onConnectionChange?.('connecting');

    try {
      const ws = new WebSocket(url);
      this.ws = ws;

      ws.onopen = () => {
        if (this.destroyed) { ws.close(); return; }
        this.reconnectAttempt = 0;
        this.lastHeartbeat = Date.now();
        this.callbacks.onConnectionChange?.('connected');

        // Subscribe to channels
        this.send({ type: 'subscribe', channels: this.subscribedChannels, seq: this.nextSeq() });

        // Start ping interval
        this.startPing();
        // Start heartbeat watchdog
        this.resetHeartbeatWatchdog();
      };

      ws.onmessage = (event) => {
        try {
          const msg: ServerMessage = JSON.parse(event.data);
          this.handleMessage(msg);
        } catch (err) {
          console.error('[WsProtocolClient] Parse error:', err);
        }
      };

      ws.onclose = () => {
        this.ws = null;
        this.stopTimers();
        this.callbacks.onConnectionChange?.('disconnected');
        this.scheduleReconnect();
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch (e) {
      console.error('[WsProtocolClient] Connection failed:', e);
      this.callbacks.onConnectionChange?.('disconnected');
      this.scheduleReconnect();
    }
  }

  private handleMessage(msg: ServerMessage): void {
    switch (msg.type) {
      case 'pong':
        break; // No-op; ping/pong is just for latency monitoring
      case 'heartbeat':
        this.lastHeartbeat = Date.now();
        this.resetHeartbeatWatchdog();
        break;
      case 'status_update':
        this.callbacks.onStatusUpdate?.(msg.payload);
        break;
      case 'task_event':
        this.callbacks.onTaskEvent?.(msg.payload);
        break;
      case 'error':
        this.callbacks.onError?.(msg.code, msg.message);
        break;
    }
  }

  private send(msg: ClientMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      this.send({ type: 'ping', seq: this.nextSeq() });
    }, PING_INTERVAL_MS);
  }

  private stopPing(): void {
    if (this.pingTimer) { clearInterval(this.pingTimer); this.pingTimer = null; }
  }

  private resetHeartbeatWatchdog(): void {
    if (this.heartbeatTimer) clearTimeout(this.heartbeatTimer);
    this.heartbeatTimer = setTimeout(() => {
      // No heartbeat received within timeout — connection is dead
      console.warn('[WsProtocolClient] Heartbeat timeout — reconnecting');
      this.close();
    }, HEARTBEAT_TIMEOUT_MS);
  }

  private scheduleReconnect(): void {
    if (this.destroyed) return;
    this.callbacks.onConnectionChange?.('connecting');
    const delay = RECONNECT_DELAYS[this.reconnectAttempt] || RECONNECT_DELAYS[RECONNECT_DELAYS.length - 1];
    const jitter = Math.round((Math.random() * 2 - 1) * JITTER_RANGE);
    this.reconnectAttempt = Math.min(this.reconnectAttempt + 1, RECONNECT_DELAYS.length - 1);
    this.reconnectTimer = setTimeout(() => {
      const url = this.wsUrl();
      if (url) this.connect(url);
    }, delay + jitter);
  }

  private wsUrl(): string | null {
    if (typeof window === 'undefined') return null;
    return `ws://${window.location.hostname}:8000/ws/status`;
  }

  private stopTimers(): void {
    this.stopPing();
    if (this.heartbeatTimer) { clearTimeout(this.heartbeatTimer); this.heartbeatTimer = null; }
  }

  close(): void {
    this.destroyed = true;
    this.stopTimers();
    if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
  }

  /** Send pong in response to server ping */
  pong(seq: number): void {
    this.send({ type: 'pong', seq });
  }
}
