'use client';

import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

/**
 * Designed empty state for any list/grid/panel.
 * Provides a clear explanation and a single primary action.
 */
export default function EmptyState({
  title,
  description,
  icon,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className={`h-full min-h-[200px] flex flex-col items-center justify-center text-center gap-2 p-6 ${className}`}
    >
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center"
        style={{ background: 'var(--brand-primary-soft)', color: 'var(--brand-primary)' }}
        aria-hidden="true"
      >
        {icon ?? <Inbox className="w-5 h-5" />}
      </div>
      <h3 className="text-sm font-bold text-[var(--text-primary)] mt-1">{title}</h3>
      {description ? (
        <p className="text-[11px] text-[var(--text-muted)] max-w-[280px] leading-relaxed">
          {description}
        </p>
      ) : null}
      {action ? (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-3 h-8 px-3 inline-flex items-center text-xs font-semibold rounded-md text-white transition-colors"
          style={{ background: 'var(--brand-primary)' }}
        >
          {action.label}
        </button>
      ) : null}
    </div>
  );
}
