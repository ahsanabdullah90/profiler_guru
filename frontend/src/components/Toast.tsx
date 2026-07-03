'use client';

import { useStatusStore } from '../store/statusStore';
import { X, AlertCircle, AlertTriangle, Info } from 'lucide-react';

const ICONS = {
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
} as const;

const COLORS = {
  error: {
    bg: 'rgba(255, 90, 95, 0.08)',
    border: 'var(--error)',
    text: 'var(--error)',
    icon: 'var(--error)',
  },
  warning: {
    bg: 'rgba(245, 165, 36, 0.08)',
    border: 'var(--warning)',
    text: 'var(--warning)',
    icon: 'var(--warning)',
  },
  info: {
    bg: 'var(--brand-primary-soft)',
    border: 'var(--brand-primary)',
    text: 'var(--brand-primary)',
    icon: 'var(--brand-primary)',
  },
} as const;

export default function Toast() {
  const errors = useStatusStore((s) => s.errors);
  const dismissError = useStatusStore((s) => s.dismissError);

  if (errors.length === 0) return null;

  return (
    <div
      className="fixed bottom-16 right-4 z-50 flex flex-col gap-2 max-w-sm"
      role="alert"
      aria-live="assertive"
    >
      {errors.map((err) => {
        const Icon = ICONS[err.type] || ICONS.info;
        const palette = COLORS[err.type] || COLORS.info;
        return (
          <div
            key={err.id}
            className="flex items-start gap-2 p-2.5 rounded-md border backdrop-blur-md shadow-xl animate-in slide-in-from-right"
            style={{
              background: palette.bg,
              borderColor: palette.border,
            }}
          >
            <Icon
              className="w-4 h-4 shrink-0 mt-0.5"
              style={{ color: palette.icon }}
              aria-hidden="true"
            />
            <p
              className="text-[11px] leading-relaxed flex-1 text-[var(--text-primary)]"
              role="status"
            >
              {err.message}
            </p>
            <button
              type="button"
              onClick={() => dismissError(err.id)}
              className="shrink-0 opacity-60 hover:opacity-100 transition-opacity p-0.5 rounded"
              style={{ color: palette.text }}
              aria-label={`Dismiss ${err.type}: ${err.message}`}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
