'use client';

import React from 'react';

export type SurfaceVariant = 'flat' | 'raised' | 'inset' | 'header' | 'sidebar';

interface SurfaceProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: SurfaceVariant;
  as?: keyof React.JSX.IntrinsicElements;
}

const VARIANT_CLASSES: Record<SurfaceVariant, string> = {
  flat: 'bg-[var(--bg-surface)] border border-[var(--border-subtle)]',
  raised: 'bg-[var(--bg-surface-raised)] border border-[var(--border-subtle)]',
  inset: 'bg-[var(--bg-surface-inset)] border border-[var(--border-subtle)]',
  header: 'bg-[var(--bg-surface-raised)] border-b border-[var(--border-subtle)]',
  sidebar: 'bg-[var(--bg-surface-raised)] border-r border-[var(--border-subtle)]',
};

export default function Surface({
  variant = 'flat',
  as: Tag = 'div',
  className = '',
  children,
  ...rest
}: SurfaceProps) {
  const Component = Tag as React.ElementType;
  return (
    <Component
      className={`${VARIANT_CLASSES[variant]} ${className}`}
      {...rest}
    >
      {children}
    </Component>
  );
}
