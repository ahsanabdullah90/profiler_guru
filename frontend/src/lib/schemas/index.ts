import { z } from 'zod';

// ── Contact ────────────────────────────────────────────────────────────────────

export const ContactSchema = z.object({
  name: z.string(),
  msg_count: z.number(),
  last_date: z.string(),
  last_snippet: z.string(),
  avg_msg: z.number(),
  indexed_chunks: z.number(),
  rag_progress: z.number(),
  depth_label: z.string(),
  depth_color: z.string(),
});
export type Contact = z.infer<typeof ContactSchema>;

// ── Message ────────────────────────────────────────────────────────────────────

export const MessageSchema = z.object({
  id: z.string(),
  sender: z.string(),
  time: z.string(),
  text: z.string(),
  audio_url: z.string().nullable(),
  is_self: z.boolean(),
});
export type Message = z.infer<typeof MessageSchema>;

// ── Analytics ──────────────────────────────────────────────────────────────────

export const TimelineEntrySchema = z.object({
  date: z.string(),
  messages: z.number(),
});

export const AnalyticsSchema = z.object({
  avg_msg_weekly: z.number(),
  avg_msg_monthly: z.number(),
  depth_label: z.string(),
  depth_color: z.string(),
  timeline: z.array(TimelineEntrySchema),
  total_messages: z.number(),
  audio_count: z.number(),
  audio_ratio: z.number(),
});
export type Analytics = z.infer<typeof AnalyticsSchema>;

// ── System Status ──────────────────────────────────────────────────────────────

const SyncStatusSchema = z.object({
  status: z.enum(['idle', 'syncing']),
  contact: z.string(),
  current: z.number(),
  total: z.number(),
});

const TranscriptionStatusSchema = z.object({
  status: z.enum(['idle', 'transcribing']),
  contact: z.string(),
  current: z.number(),
  total: z.number(),
});

const RagStatusSchema = z.object({
  status: z.enum(['idle', 'indexing']),
  contact: z.string(),
  progress: z.number(),
});

const LlmStatusSchema = z.object({
  model: z.string(),
  online: z.boolean(),
});

export const SystemStatusSchema = z.object({
  app_online: z.boolean(),
  instagram_sync: SyncStatusSchema,
  transcription: TranscriptionStatusSchema,
  rag: RagStatusSchema,
  online_llm: LlmStatusSchema,
  ollama: LlmStatusSchema,
});
export type SystemStatus = z.infer<typeof SystemStatusSchema>;

// ── Profile ────────────────────────────────────────────────────────────────────

export const ProfileMetaSchema = z.object({
  start_month: z.string(),
  end_month: z.string(),
  model: z.string().optional(),
});

export const ProfileResponseSchema = z.object({
  profile: z.string().nullable(),
  meta: ProfileMetaSchema.nullable(),
});
export type ProfileResponse = z.infer<typeof ProfileResponseSchema>;

// ── RAG ────────────────────────────────────────────────────────────────────────

export const RAGResponseSchema = z.object({
  response: z.string(),
});
export type RAGResponse = z.infer<typeof RAGResponseSchema>;

export const GlobalSearchResultSchema = z.object({
  id: z.string(),
  chat_name: z.string(),
  month: z.string(),
  document: z.string(),
});
export const GlobalSearchResponseSchema = z.array(GlobalSearchResultSchema);
export type GlobalSearchResponse = z.infer<typeof GlobalSearchResponseSchema>;

// ── Settings ───────────────────────────────────────────────────────────────────

export const SettingsResponseSchema = z.object({
  settings: z.record(z.string(), z.any()),
  installed_ollama_models: z.array(z.string()),
  best_local_model: z.string(),
  has_google_key: z.boolean(),
});
export type SettingsResponse = z.infer<typeof SettingsResponseSchema>;

// ── Auth ───────────────────────────────────────────────────────────────────────

export const TokenResponseSchema = z.object({
  token: z.string(),
  token_type: z.string().optional(),
});
export type TokenResponse = z.infer<typeof TokenResponseSchema>;

export const VerifyResponseSchema = z.object({
  status: z.literal('valid'),
});

// ── Instagram ──────────────────────────────────────────────────────────────────

export const InstagramStatusSchema = z.object({
  logged_in: z.boolean(),
  username: z.string(),
  active_syncs: z.array(z.string()),
  daemon_sync_active: z.boolean(),
  challenge_url: z.string().nullable(),
  two_factor_required: z.boolean().optional(),
});
export type InstagramStatus = z.infer<typeof InstagramStatusSchema>;
