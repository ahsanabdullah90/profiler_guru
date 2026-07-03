'use client';

import React from 'react';

interface InspectorSectionProps {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

/**
 * Sectioned layout primitive used by the Inspector pane.
 * Provides a uniform vertical rhythm and section header.
 */
export default function InspectorSection({
  title,
  description,
  actions,
  children,
  className = '',
}: InspectorSectionProps) {
  return (
    <section
      className={`py-3 first:pt-0 last:pb-0 border-b border-[var(--border-subtle)] last:border-b-0 ${className}`}
      aria-labelledby={title ? `inspector-section-${title.replace(/\s+/g, '-').toLowerCase()}` : undefined}
    >
      {title ? (
        <header className="flex items-center justify-between mb-2">
          <div>
            <h3
              id={`inspector-section-${title.replace(/\s+/g, '-').toLowerCase()}`}
              className="text-[9px] uppercase tracking-wider text-[var(--text-muted)] font-bold"
            >
              {title}
            </h3>
            {description ? (
              <p className="text-[10px] text-[var(--text-muted)] mt-0.5">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex items-center gap-1.5">{actions}</div> : null}
        </header>
      ) : null}
      <div>{children}</div>
    </section>
  );
}
