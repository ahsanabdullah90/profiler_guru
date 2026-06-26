'use client';

import { useSyncStore } from '../store/useSyncStore';
import { X, AlertCircle, AlertTriangle, Info } from 'lucide-react';

const ICONS = {
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
} as const;

const COLORS = {
  error: {
    bg: 'rgba(255,55,95,0.1)',
    border: 'rgba(255,55,95,0.25)',
    text: '#FF375F',
    icon: '#FF375F',
  },
  warning: {
    bg: 'rgba(255,149,0,0.08)',
    border: 'rgba(255,149,0,0.2)',
    text: '#FF9500',
    icon: '#FF9500',
  },
  info: {
    bg: 'rgba(0,122,255,0.08)',
    border: 'rgba(0,122,255,0.2)',
    text: '#007AFF',
    icon: '#007AFF',
  },
} as const;

export default function Toast() {
  const errors = useSyncStore(s => s.errors);
  const dismissError = useSyncStore(s => s.dismissError);

  if (errors.length === 0) return null;

  return (
    <div className="fixed bottom-16 right-6 z-50 flex flex-col gap-2 max-w-sm">
      {errors.map((err) => {
        const Icon = ICONS[err.type] || ICONS.info;
        const palette = COLORS[err.type] || COLORS.info;
        return (
          <div
            key={err.id}
            className="flex items-start gap-2 p-3 rounded-lg border backdrop-blur-md shadow-xl animate-in slide-in-from-right"
            style={{
              background: palette.bg,
              borderColor: palette.border,
            }}
          >
            <Icon className="w-4 h-4 shrink-0 mt-0.5" style={{ color: palette.icon }} />
            <p className="text-[11px] leading-relaxed flex-1" style={{ color: palette.text }}>
              {err.message}
            </p>
            <button
              onClick={() => dismissError(err.id)}
              className="shrink-0 opacity-50 hover:opacity-100 transition-opacity cursor-pointer"
              style={{ color: palette.text }}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
